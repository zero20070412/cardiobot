import gradio as gr
import os
import uuid
from frontend.sidebar import create_sidebar
from frontend.chart_panel import create_chart_panel
from frontend.chat_panel import create_chat_panel
# 🌟 新增导入 clear_session_history 
from agent.core import get_agent_response, clear_session_history
from agent.prompts import CARDIO_ASSISTANT_PROMPT

SESSION_ID = str(uuid.uuid4())

gemini_ultimate_css = """
.gradio-container { background-color: #ffffff !important; }
.gr-panel, .gr-block { border: none !important; box-shadow: none !important; }

/* 1. 胶囊容器：确保垂直方向内容居中 */
#gemini-capsule-row {
    background-color: #FFFFFF !important;
    border: 1px solid #E8EAED !important;
    border-radius: 32px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
    padding: 6px 16px !important;
    display: flex !important;
    align-items: center !important;
}

/* 2. 输入框去除边框 */
#gemini-input-box textarea {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    font-size: 16px !important;
}

/* 3. 图标按钮通用容器 */
#safety-icon, #mic-icon, #gemini-send-btn {
    background: transparent !important;
    border: none !important;
    min-width: 44px !important;
    max-width: 44px !important;
    height: 44px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

/* 4. 麦克风图标 */
#mic-icon img {
    width: 28px !important;
    height: 28px !important;
    object-fit: contain !important;
    transform: scale(1.3) !important; 
    transform-origin: center !important;
}

/* 5. 发送按钮样式 */
#gemini-send-btn {
    background-color: #F1F3F4 !important;
    border-radius: 50% !important;
    color: #202124 !important;
    font-size: 18px !important;
}
"""

def handle_chat(user_message, chat_history):
    if not user_message: return "", chat_history
    try:
        response = get_agent_response(user_message=user_message, session_id=SESSION_ID, system_prompt=CARDIO_ASSISTANT_PROMPT)
        reply = response.get("reply", "...")
        
        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": reply})
        return "", chat_history
    except Exception as e:
        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": f"❌ 系统错误: {str(e)}"})
        return "", chat_history

def toggle_ui(text):
    """动态切换麦克风与发送按钮"""
    is_empty = len(text.strip()) == 0
    return gr.update(visible=is_empty), gr.update(visible=not is_empty)

def start_new_chat():
    """清空后端记忆，并返回空列表以清空前端聊天界面"""
    clear_session_history(SESSION_ID)
    gr.Info("已开启新对话！")
    return []


def show_history():

    gr.Info("历史对话面板正在开发中...")

with gr.Blocks(title="CardioBot") as demo:
    gr.Markdown("# CardioBot 健康助手")
    with gr.Row():
        with gr.Column(scale=2):
            up_btn, new_btn, clr_btn = create_sidebar()
        with gr.Column(scale=8):
            chat_box, input_box, send_b, mic_b = create_chat_panel()
            _, hrv_s, stress_s, tips_t = create_chart_panel()


    input_box.change(fn=toggle_ui, inputs=[input_box], outputs=[mic_b, send_b])
    send_b.click(handle_chat, [input_box, chat_box], [input_box, chat_box])
    input_box.submit(handle_chat, [input_box, chat_box], [input_box, chat_box])


    new_btn.click(fn=start_new_chat, inputs=[], outputs=[chat_box])
    
    clr_btn.click(fn=show_history, inputs=[], outputs=[])

if __name__ == "__main__":
    root_path = os.path.dirname(os.path.abspath(__file__))
    demo.launch(css=gemini_ultimate_css, allowed_paths=[root_path])