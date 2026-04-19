import gradio as gr
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
mic_icon_path = os.path.join(current_dir, "213麦克风.png")

def create_chat_panel():
    with gr.Column():
        chatbot = gr.Chatbot(label=None, show_label=False, height=500)
        
        with gr.Row(elem_id="gemini-capsule-row"):
            # 左侧安全图标
            gr.Button("", elem_id="safety-icon", interactive=False)
            
            # 中间输入框
            msg_input = gr.Textbox(
                placeholder="发信息或按住说话",
                container=False,
                show_label=False,
                elem_id="gemini-input-box",
                scale=20
            )
            
            # 右侧：使用修正后的相对路径加载图片
            voice_btn = gr.Button(
                value="", 
                icon=mic_icon_path, 
                elem_id="mic-icon", 
                visible=True
            )
            
            # 发送按钮
            send_btn = gr.Button("➔", elem_id="gemini-send-btn", visible=False)
        
    return chatbot, msg_input, send_btn, voice_btn