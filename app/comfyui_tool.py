import json
import os
import dotenv
import websocket  
import uuid
import httpx
import urllib.parse
import random
import pandas as pd

dotenv.load_dotenv(override=True)

SD_LORA = os.getenv('SD_LORA')

class ComfyUITool:
    def __init__(self, server_address, seed, workflowfile, working_dir):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())  # 生成一个唯一的客户端ID
        self.seed = seed
        self.workflowfile = workflowfile
        self.working_dir = working_dir

    def show_gif(self, fname):
        import base64
        from IPython import display
        with open(fname, 'rb') as fd:
            b64 = base64.b64encode(fd.read()).decode('ascii')
        return display.HTML(f'<img src="data:image/gif;base64,{b64}" />')

    def queue_prompt(self, prompt):
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        with httpx.Client() as client:
            response = client.post("http://{}/prompt".format(self.server_address), data=data)
            return response.json()

    def get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        url = "http://{}/view?{}".format(self.server_address, url_values)
        with httpx.Client() as client:
            response = client.get(url)
            return response.content
    def free(self):
        p = {"unload_models": "true", "free_memory": "true"}
        data = json.dumps(p).encode('utf-8')
        with httpx.Client() as client:
            client.post("http://{}/free".format(self.server_address), data=data)
            return True

    def get_history(self, prompt_id):
    	with httpx.Client() as client:
            response = client.get("http://{}/history/{}".format(self.server_address, prompt_id))
            return response.json()

    def get_images(self, ws, prompt):
        prompt_id = self.queue_prompt(prompt)['prompt_id']
        output_images = {}
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        break  
            else:
                continue  

        history = self.get_history(prompt_id)[prompt_id]
        for o in history['outputs']:
            for node_id in history['outputs']:
                node_output = history['outputs'][node_id]
                # 图片分支
                if 'images' in node_output:
                    images_output = []
                    for image in node_output['images']:
                        image_data = self.get_image(image['filename'], image['subfolder'], image['type'])
                        images_output.append(image_data)
                    output_images[node_id] = images_output
                # 视频分支
                if 'videos' in node_output:
                    videos_output = []
                    for video in node_output['videos']:
                        video_data = self.get_image(video['filename'], video['subfolder'], video['type'])
                        videos_output.append(video_data)
                    output_images[node_id] = videos_output
        return output_images

    def parse_worflow(self, ws, prompt):
        # 获取工作流文件路径
        workflowfile = self.workflowfile
        # 打开工作流文件并加载JSON数据
        with open(workflowfile, 'r', encoding="utf-8") as workflow_api_txt2gif_file:
            prompt_data = json.load(workflow_api_txt2gif_file)
            ### 注意这里根据自己的工作流修改, 这里是替换prompt 节点的代码。
            prompt_data["6"]["inputs"]["text"] = prompt+ SD_LORA
            return self.get_images(ws, prompt_data)

    def generate_clip(self, prompt, idx=1):
        ws = websocket.WebSocket()
        ws.connect("ws://{}/ws?clientId={}".format(self.server_address, self.client_id))
        images = self.parse_worflow(ws, prompt)
        raw_images = []
        for node_id in images:
            for image_data in images[node_id]:
                raw_images.append(image_data)
        return raw_images
    
    def read_prompts_from_excel(self, csv_file_path):
        df = pd.read_excel(csv_file_path)
        return df['prompt'].tolist()
    
if __name__ == "__main__":
    # 设置工作目录和项目相关的路径
    server_address = '127.0.0.1:8188'
    workflow_file = 'data/nunchaku-flux.1-dev.json'
    workfolw_seed = 162434675638754  # workflowfile 开头总的中的seed
    output_dir= 'output'

    # 创建 ComfyUITool 实例
    comfyui_tool = ComfyUITool(server_address, workfolw_seed, workflow_file, output_dir)
    prompt = "style, sunset,The night had not fully lifted,and the coastal city was still slumbering.\
          The waves gently lapped the beach,playing a tender overture. A faint light emerged \
          on the horizon,gradually changing from pale white to golden yellow,slowly outlining \
          the city's silhouette. "
    ## 更换提示词生成图片
    image =  comfyui_tool.generate_clip(prompt)
    print(f"生成图片成功: {type(image[0])}")
    comfyui_tool.free()
