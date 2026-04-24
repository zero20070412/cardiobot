import gradio as gr
from agent.history_manager import get_history_choices # 确保导入了 manager

def create_sidebar():
    with gr.Column(variant="panel"):
        up_btn = gr.File(label="上传体检单", file_types=[".pdf", ".jpg"])
        new_btn = gr.Button("新对话", variant="primary")
        
        # 【改动】必须使用 Dropdown 才能支持切换历史，且 value 设为 None 避免初始报错
        history_dropdown = gr.Dropdown(
            label="历史对话记录", 
            choices=get_history_choices(),
            interactive=True,
            value=None
        )
        
    return up_btn, new_btn, history_dropdown