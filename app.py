import gradio as gr
import os
import uuid
import time  # 导入时间库以实现打字机流式效果
from frontend.sidebar import create_sidebar
from frontend.chart_panel import create_chart_panel
from frontend.chat_panel import create_chat_panel
from agent.core import get_agent_response, clear_session_history
from agent.prompts import CARDIO_ASSISTANT_PROMPT

SESSION_ID = str(uuid.uuid4())

# CSS 样式保持不变
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

/* 思考中动画样式：跳动的呼吸圆点 */
.thinking-container {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 0;
}

.thinking-dot {
    width: 8px;
    height: 8px;
    background-color: #4285F4; /* 使用和发送按钮接近的蓝色 */
    border-radius: 50%;
    opacity: 0.4;
    animation: thinking-bounce 1.4s infinite ease-in-out both;
}

.thinking-dot:nth-child(1) { animation-delay: -0.32s; }
.thinking-dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes thinking-bounce {
    0%, 80%, 100% { 
        transform: scale(0.8);
        opacity: 0.4;
    } 
    40% { 
        transform: scale(1.2);
        opacity: 1;
    }
}

.gradio-container .gr-panel { margin-top: 0 !important; }
#sidebar-container { padding-top: 0 !important; margin-top: 0 !important; }
.gr-block.gr-box { margin-top: 0 !important; }
"""

# --- 逻辑处理函数 ---

def handle_chat(user_text, user_audio, input_mode, chat_history):
    # 1. 获取用户输入
    if input_mode == "text":
        if not user_text: 
            yield "", None, chat_history
            return
        user_message = user_text
    else:
        if not user_audio: 
            yield "", None, chat_history
            return
        user_message = f"🎵 [接收到语音文件]"

    # 2. 立即显示用户消息
    chat_history.append({"role": "user", "content": user_message})
    
    # 3. 注入【呼吸动画】占位符
    # 这里的 HTML 结构会触发我们上面定义的 CSS 动画
    thinking_html = """
    <div class="thinking-container">
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
        <div class="thinking-dot"></div>
    </div>
    """
    chat_history.append({"role": "assistant", "content": thinking_html}) 
    yield "", None, chat_history

    try:
        # 4. 获取 AI 响应 (API 请求期间，界面会保持显示动画)
        response = get_agent_response(
            user_message=user_message, 
            session_id=SESSION_ID, 
            system_prompt=CARDIO_ASSISTANT_PROMPT
        )
        full_reply = response.get("reply", "...")
        
        # 5. 开始打字前，清空动画占位符
        chat_history[-1]["content"] = "" 
        
        # 6. 流式输出文字
        current_text = ""
        for char in full_reply:
            current_text += char
            chat_history[-1]["content"] = current_text
            yield "", None, chat_history
            time.sleep(0.01) 

    except Exception as e:
        chat_history[-1]["content"] = f"❌ 系统错误: {str(e)}"
        yield "", None, chat_history

def toggle_input_mode(current_mode, mic_path, kb_path):
    """
    切换文本/语音输入模式
    """
    if current_mode == "text":
        return "audio", gr.update(visible=False), gr.update(visible=True), gr.update(icon=kb_path)
    else:
        return "text", gr.update(visible=True), gr.update(visible=False), gr.update(icon=mic_path)

def start_new_chat():
    clear_session_history(SESSION_ID)
    gr.Info("已开启新对话！")
    return []

def show_history():
    gr.Info("历史对话面板正在开发中...")

# --- Gradio 界面布局 ---

with gr.Blocks(title="CardioBot") as demo:
    gr.Markdown("# CardioBot 健康助手")
    
    input_mode = gr.State("text")
    
    with gr.Row():
        with gr.Column(scale=2):
            up_btn, new_btn, clr_btn = create_sidebar()
        with gr.Column(scale=8):
            # 获取组件
            chat_box, input_box, audio_box, toggle_b, send_b, mic_path, kb_path = create_chat_panel()
            _, hrv_s, stress_s, tips_t = create_chart_panel()

    # --- 事件绑定 ---

    # 切换模式
    toggle_b.click(
        fn=toggle_input_mode,
        inputs=[input_mode, gr.State(mic_path), gr.State(kb_path)],
        outputs=[input_mode, input_box, audio_box, toggle_b]
    )

    # 发送按钮点击 (流式)
    send_b.click(
        fn=handle_chat, 
        inputs=[input_box, audio_box, input_mode, chat_box], 
        outputs=[input_box, audio_box, chat_box],
        show_progress="hidden"
    )
    
    # 文本框回车提交 (流式)
    input_box.submit(
        fn=handle_chat, 
        inputs=[input_box, audio_box, input_mode, chat_box], 
        outputs=[input_box, audio_box, chat_box],
        show_progress="hidden"
    )

    # 侧边栏按钮
    new_btn.click(fn=start_new_chat, inputs=[], outputs=[chat_box])
    clr_btn.click(fn=show_history, inputs=[], outputs=[])

if __name__ == "__main__":
    root_path = os.path.dirname(os.path.abspath(__file__))
    # 启动应用
    demo.launch(css=gemini_ultimate_css, allowed_paths=[root_path])