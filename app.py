import gradio as gr
import os
import uuid
import time
from frontend.sidebar import create_sidebar
from frontend.chart_panel import create_chart_panel
from frontend.chat_panel import create_chat_panel
from agent.core import get_agent_response, clear_session_history
from agent.prompts import CARDIO_ASSISTANT_PROMPT
from agent.history_manager import save_session, get_history_choices, get_session_history

# 初始化全局会话 ID
SESSION_ID = str(uuid.uuid4())

gemini_ultimate_css = """
.gradio-container { background-color: #ffffff !important; }
.gr-panel, .gr-block { border: none !important; box-shadow: none !important; }

#gemini-capsule-row {
    background-color: #FFFFFF !important;
    border: 1px solid #E8EAED !important;
    border-radius: 32px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
    padding: 6px 16px !important;
    display: flex !important;
    align-items: flex-end !important;
    gap: 4px !important;
}

#gemini-input-box textarea {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    font-size: 16px !important;
    padding-left: 4px !important;
    padding-top: 10px !important;
    padding-bottom: 10px !important;
}
#gemini-input-box textarea:focus {
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}
#gemini-input-box .container {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}

#gemini-audio-box {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    margin-left: -8px !important;
}
#gemini-audio-box button[aria-label="Clear"] {
    display: none !important;
}

#toggle-icon, #gemini-send-btn {
    background: transparent !important;
    border: none !important;
    min-width: 44px !important;
    max-width: 44px !important;
    height: 44px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin-bottom: 2px !important;
}

#toggle-icon img {
    width: 28px !important;
    height: 28px !important;
    object-fit: contain !important;
    transform: scale(1.3) !important; 
    transform-origin: center !important;
}

#gemini-send-btn {
    background-color: #F1F3F4 !important;
    border-radius: 50% !important;
    color: #202124 !important;
    font-size: 18px !important;
}

.thinking-container {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 0;
}

.thinking-dot {
    width: 8px;
    height: 8px;
    background-color: #4285F4;
    border-radius: 50%;
    opacity: 0.4;
    animation: thinking-bounce 1.4s infinite ease-in-out both;
}

.thinking-dot:nth-child(1) { animation-delay: -0.32s; }
.thinking-dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes thinking-bounce {
    0%, 80%, 100% { transform: scale(0.8); opacity: 0.4; } 
    40% { transform: scale(1.2); opacity: 1; }
}
"""

def handle_chat(user_text, user_audio, input_mode, chat_history):
    global SESSION_ID
    
    if input_mode == "text":
        if not isinstance(user_text, str) or user_text.strip() == "":
            yield "", None, chat_history, gr.update()
            return
        user_message = user_text.strip()
    else:
        if not user_audio: 
            yield "", None, chat_history, gr.update()
            return
        user_message = "[接收到语音文件]" 

    chat_history.append({"role": "user", "content": user_message})
    thinking_html = '<div class="thinking-container"><div class="thinking-dot"></div><div class="thinking-dot"></div><div class="thinking-dot"></div></div>'
    chat_history.append({"role": "assistant", "content": thinking_html}) 
    yield "", None, chat_history, gr.update()

    try:
        from agent.core import default_memory_store, clear_session_history
        conv = default_memory_store.get_session(SESSION_ID)
        
        valid_frontend_msgs = [
            m for m in chat_history[:-2] 
            if "thinking-container" not in m.get("content", "")
        ]
        mem_msgs = conv.get_messages(include_system=False)
        
        if len(mem_msgs) < len(valid_frontend_msgs):
            missing_msgs = valid_frontend_msgs[len(mem_msgs):]
            for msg in missing_msgs:
                conv.add_message(role=msg["role"], content=msg["content"])
        elif len(mem_msgs) > len(valid_frontend_msgs):
            clear_session_history(SESSION_ID)
            for msg in valid_frontend_msgs:
                conv.add_message(role=msg["role"], content=msg["content"])

        response = get_agent_response(
            user_message=user_message, 
            session_id=SESSION_ID, 
            system_prompt=CARDIO_ASSISTANT_PROMPT
        )
        full_reply = response.get("reply", "...")
        
        chat_history[-1]["content"] = "" 
        current_text = ""
        for char in full_reply:
            current_text += char
            chat_history[-1]["content"] = current_text
            yield "", None, chat_history, gr.update()
            time.sleep(0.01) 

        save_session(SESSION_ID, chat_history)
        yield "", None, chat_history, gr.update(choices=get_history_choices())
    except Exception as e:
        chat_history[-1]["content"] = f"系统错误: {str(e)}"
        yield "", None, chat_history, gr.update()

def toggle_input_mode(current_mode, mic_path, kb_path):
    if current_mode == "text":
        return "audio", gr.update(visible=False), gr.update(visible=True), gr.update(icon=kb_path)
    else:
        return "text", gr.update(visible=True), gr.update(visible=False), gr.update(icon=mic_path)

def start_new_chat():
    global SESSION_ID
    SESSION_ID = str(uuid.uuid4())
    clear_session_history(SESSION_ID)
    gr.Info("已开启新对话！")
    return [], gr.update(value=None)

def load_history(selected_session_id):
    global SESSION_ID
    if selected_session_id:
        SESSION_ID = selected_session_id
        history = get_session_history(selected_session_id)
        
        from agent.core import clear_session_history, default_memory_store
        clear_session_history(selected_session_id)
        conv = default_memory_store.get_session(selected_session_id)
        for msg in history:
            if "thinking-container" not in msg.get("content", ""):
                conv.add_message(role=msg["role"], content=msg["content"])
        return history
    return []

# Gradio 界面布局

with gr.Blocks(title="CardioBot") as demo:
    gr.Markdown("# CardioBot 健康助手")
    
    input_mode = gr.State("text")
    
    with gr.Row():
        with gr.Column(scale=2):
            up_btn, new_btn, history_dropdown = create_sidebar()
        with gr.Column(scale=8):
            chat_box, input_box, audio_box, toggle_b, send_b, mic_path, kb_path = create_chat_panel()
            _, hrv_s, stress_s, tips_t = create_chart_panel()

    toggle_b.click(
        fn=toggle_input_mode,
        inputs=[input_mode, gr.State(mic_path), gr.State(kb_path)],
        outputs=[input_mode, input_box, audio_box, toggle_b]
    )

    send_b.click(
        fn=handle_chat, 
        inputs=[input_box, audio_box, input_mode, chat_box], 
        outputs=[input_box, audio_box, chat_box, history_dropdown],
        show_progress="hidden"
    )
    
    input_box.submit(
        fn=handle_chat, 
        inputs=[input_box, audio_box, input_mode, chat_box], 
        outputs=[input_box, audio_box, chat_box, history_dropdown],
        show_progress="hidden"
    )

    new_btn.click(fn=start_new_chat, inputs=[], outputs=[chat_box, history_dropdown])
    
    history_dropdown.change(
        fn=load_history, 
        inputs=[history_dropdown], 
        outputs=[chat_box]
    )

if __name__ == "__main__":
    root_path = os.path.dirname(os.path.abspath(__file__))
    demo.launch(css=gemini_ultimate_css, allowed_paths=[root_path])