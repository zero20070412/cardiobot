import gradio as gr
import os
import uuid
from frontend.sidebar import create_sidebar
from frontend.chart_panel import create_chart_panel
from frontend.chat_panel import create_chat_panel
from agent.core import get_agent_response, clear_session_history
from agent.prompts import CARDIO_ASSISTANT_PROMPT

SESSION_ID = str(uuid.uuid4())

gemini_ultimate_css = """
.gradio-container { background-color: #ffffff !important; }
.gr-panel, .gr-block { border: none !important; box-shadow: none !important; }

/* 1. 胶囊容器：改为 flex-end 实现多行时图标沉底靠右下，调整 gap 缩小图标间距 */
#gemini-capsule-row {
    background-color: #FFFFFF !important;
    border: 1px solid #E8EAED !important;
    border-radius: 32px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
    padding: 6px 16px !important;
    display: flex !important;
    align-items: flex-end !important; /* 关键：打字多行变高时，图标停留在右下角 */
    gap: 4px !important; /* 2. 缩小右侧图标之间的间距 */
}

/* 3 & 4. 输入框样式：去内层框、去聚焦外发光、起点靠左 */
#gemini-input-box textarea {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    font-size: 16px !important;
    padding-left: 4px !important; /* 4. 起点靠左一些，但保留 4px 呼吸感，不完全挨死 */
    padding-top: 10px !important; /* 上下预留 padding 使得单行文字时与图标高度齐平 */
    padding-bottom: 10px !important;
}
/* 去除点击输入框时 Gradio 默认出现的丑陋内边框 */
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

/* 5. 语音框：靠左对齐，并删除右上角的叉叉 */
#gemini-audio-box {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    margin-left: -8px !important; /* 5. 录制图标整体再靠左一些 */
}
/* 隐藏 Gradio 默认生成的清除叉叉图标 */
#gemini-audio-box button[aria-label="Clear"] {
    display: none !important;
}

/* 图标按钮通用容器 */
#toggle-icon, #gemini-send-btn {
    background: transparent !important;
    border: none !important;
    min-width: 44px !important;
    max-width: 44px !important;
    height: 44px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin-bottom: 2px !important; /* 防止紧贴底部边界 */
}

/* 切换图标样式 */
#toggle-icon img {
    width: 28px !important;
    height: 28px !important;
    object-fit: contain !important;
    transform: scale(1.3) !important; 
    transform-origin: center !important;
}

/* 发送按钮样式 */
#gemini-send-btn {
    background-color: #F1F3F4 !important;
    border-radius: 50% !important;
    color: #202124 !important;
    font-size: 18px !important;
}
"""

def handle_chat(user_text, user_audio, input_mode, chat_history):
    # 根据当前模式提取用户消息
    if input_mode == "text":
        if not user_text: return "", None, chat_history
        user_message = user_text
        clear_text, clear_audio = "", None
    else:
        if not user_audio: return "", None, chat_history
        # ⚠️ 这里只是占位，实际业务中你需要在这里接入 Whisper 等 STT (语音转文本) API
        # text_from_audio = transcribe_audio(user_audio)
        user_message = f"🎵 [接收到语音文件，请在此处接入STT转换: {user_audio}]"
        clear_text, clear_audio = "", None

    try:
        response = get_agent_response(user_message=user_message, session_id=SESSION_ID, system_prompt=CARDIO_ASSISTANT_PROMPT)
        reply = response.get("reply", "...")
        
        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": reply})
        return clear_text, clear_audio, chat_history
    except Exception as e:
        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": f"❌ 系统错误: {str(e)}"})
        return clear_text, clear_audio, chat_history

def toggle_input_mode(current_mode, mic_path, kb_path):
    """切换文本/语音模式"""
    if current_mode == "text":
        # 变成语音模式：隐藏文本框，显示语音框，图标变键盘
        return "audio", gr.update(visible=False), gr.update(visible=True), gr.update(icon=kb_path)
    else:
        # 变成文本模式：显示文本框，隐藏语音框，图标变麦克风
        return "text", gr.update(visible=True), gr.update(visible=False), gr.update(icon=mic_path)

def start_new_chat():
    clear_session_history(SESSION_ID)
    gr.Info("已开启新对话！")
    return []

def show_history():
    gr.Info("历史对话面板正在开发中...")

with gr.Blocks(title="CardioBot") as demo:
    gr.Markdown("# CardioBot 健康助手")
    
    # 初始化状态为文本模式
    input_mode = gr.State("text")
    
    with gr.Row():
        with gr.Column(scale=2):
            up_btn, new_btn, clr_btn = create_sidebar()
        with gr.Column(scale=8):
            # 获取所有组件以及图标的路径
            chat_box, input_box, audio_box, toggle_b, send_b, mic_path, kb_path = create_chat_panel()
            _, hrv_s, stress_s, tips_t = create_chart_panel()

    # 1. 点击切换按钮（麦克风/键盘）时的逻辑
    toggle_b.click(
        fn=toggle_input_mode,
        inputs=[input_mode, gr.State(mic_path), gr.State(kb_path)],
        outputs=[input_mode, input_box, audio_box, toggle_b]
    )

    # 2. 点击发送按钮的逻辑
    send_b.click(
        fn=handle_chat, 
        inputs=[input_box, audio_box, input_mode, chat_box], 
        outputs=[input_box, audio_box, chat_box]
    )
    
    # 3. 文本框回车的逻辑
    input_box.submit(
        fn=handle_chat, 
        inputs=[input_box, audio_box, input_mode, chat_box], 
        outputs=[input_box, audio_box, chat_box]
    )

    new_btn.click(fn=start_new_chat, inputs=[], outputs=[chat_box])
    clr_btn.click(fn=show_history, inputs=[], outputs=[])

if __name__ == "__main__":
    root_path = os.path.dirname(os.path.abspath(__file__))
    demo.launch(css=gemini_ultimate_css, allowed_paths=[root_path])