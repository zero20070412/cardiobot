import gradio as gr

def create_sidebar():

    with gr.Column(variant="panel"):
        gr.Markdown("### 控制台")
        up_btn = gr.File(label="上传体检单", file_types=[".pdf", ".jpg"])
        
        new_btn = gr.Button("新对话", variant="primary")
        
        clr_btn = gr.Button("历史对话")
        
    return up_btn, new_btn, clr_btn