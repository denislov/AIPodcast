import gc
import json
import os
import random
import time
from dotenv import load_dotenv
from moviepy import AudioClip, AudioFileClip, ColorClip, ImageClip, CompositeVideoClip, TextClip, concatenate_audioclips, concatenate_videoclips,vfx
from openai import OpenAI
import requests

from app import audio, prompt, video
from app.comfyui_tool import ComfyUITool

load_dotenv()

class TopicGenerator:
    DRAW_PROMPT_TEMPLATE = '''
Black stick figure, pure white background, vector graphic, icon design, illustration, minimalist, simple, 
    '''
    PROMPT = '''
# 角色
你是一位杰出的心理学文案大师，尤其擅长短视频文案创作。能根据用户给出的材料进行拓展，创作出每句话都极具吸引力、反差感强烈的文案，且文案前三秒必须有能抓住人心的钩子。同时，你还能针对文案中的每一句话，创作出与之对应的使用的图片描述词，描述词需要有统一的风格(铅笔画，水彩画，动漫风...，等中只选一种用于所有分镜)，不少于30字

## 技能
### 技能1:创作心理学短视频文案
1. 当用户提供材料后，确定文案主题，然后构思一个具有强烈反差感且吸引人的钩子作为文案开头。
2. 围绕主题展开，通过先举出反例再进行正面解释的方式创作文案，一句话不超过50字，要有深度。

### 技能2:编写图片描述词
1. 针对文案中的每句话，创作对应的图片描述词(分中文版和英文版)
2. 图片描述词要突出当前句子对应的重点人物姿势或物品，且描述词不得低于30字。

## 限制
- 只围绕用户提供的材料进行文案主题确定、内容创作及图片描述词编写，拒绝回答与主题无关的话题。
- 文案必须按照先举反例再正面解释，一句话不超过50字求创作图片描述词需符合规定格式。
- 确保文案和图片描述词内容符合短视频风格需求。

EXAMPLE JSON OUTPUT:
{
    "response": [
        {
            "id": "1",
            "text": "xxx",
            "prompt_zh": "xxxxx",
            "prompt_en": "xxxxx",
        }
    ]
}
'''

    def __init__(self, topic :str,cailiao:str):
        self.topic = topic
        self.cailiao = cailiao
        self.api_key = "sk-8b69f82630e14ea49260202ed152572b"
        self.base_url="https://api.deepseek.com"
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        # 初始化ComfyUITool
        url = os.getenv("COMFYUI_API_URL")
        workflow_file = 'data/nunchaku-turbo-dev.json'
        workflow_seed = 162434675638754  # workflowfile开头总的seed
        output_dir = 'output'
        self.comfyui_tool = ComfyUITool(url, workflow_seed, workflow_file, output_dir)

    def _create_image(self, prompt: str):
        """用AI生成画面"""
        image = self.comfyui_tool.generate_clip(self.DRAW_PROMPT_TEMPLATE + prompt)
        return image[0]
    
    def generate_images(self):
        if os.path.exists(f"data/topic/{self.topic}/images/.compeleted"):
            print("任务已完成，跳过")
            return True
        
        os.makedirs(f"data/topic/{self.topic}/images", exist_ok=True)

        topic_json_path = f"data/topic/{self.topic}/topic.json"

        if not os.path.exists(topic_json_path):
            raise Exception(f"文件不存在: {topic_json_path}")
        
        with open(topic_json_path, 'r', encoding='utf-8') as f:
            topic_json = json.load(f)

        for item in topic_json:
            prompt = item["prompt_en"]
            image_path = os.path.join(f"data/topic/{self.topic}/images", f"{item['id']}.png")
            if os.path.exists(image_path):
                print(f"图片已存在: {image_path}")
                continue
            image = self._create_image(prompt)
            with open(image_path, "wb") as binary_file:
                    binary_file.write(image)
            del image
            gc.collect()
            item["image"] = image_path

        with open(topic_json_path, 'w', encoding='utf-8') as f:
            json.dump(topic_json, f, ensure_ascii=False, indent=2)

        with open(f"data/topic/{self.topic}/images/.compeleted", 'w', encoding='utf-8') as f:
            f.write("done")
        self.comfyui_tool.free()
        return True
    
    def _generate_audio(self, text: str, max_retries=3):
        url = os.getenv("AUDIO_API_URL")
        api_key = os.getenv("AUDIO_API_KEY")
        model = os.getenv("AUDIO_MODEL")
        keys = api_key.split(",")
        random_key = random.choice(keys)

        payload = {
            "model": model,
            "input": text,
            "voice": "FunAudioLLM/CosyVoice2-0.5B:alex",
            "response_format": "mp3",
            "sample_rate": 44100,
            "speed":1.1,
        }
        headers = {
            "Authorization": f"Bearer {random_key}",
            "Content-Type": "application/json",
        }

        for retry in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    return response.content
                else:
                    time.sleep(1)  # 休息一秒再重试
            except Exception as e:
                if retry == max_retries - 1:  # 只在最后一次重试失败时记录日志
                    print(f"生成音频出错：{str(e)}")
                time.sleep(1)

        return None

    def generate_audio(self):
        if os.path.exists(f"data/topic/{self.topic}/audios/.compeleted"):
            print("任务已完成，跳过")
            return True
        
        os.makedirs(f"data/topic/{self.topic}/audios", exist_ok=True)

        topic_json_path = f"data/topic/{self.topic}/topic.json"

        if not os.path.exists(topic_json_path):
            raise Exception(f"文件不存在: {topic_json_path}")
        
        with open(topic_json_path, 'r', encoding='utf-8') as f:
            topic_json = json.load(f)
        for item in topic_json:
            prompt = item["text"]
            audio_path = os.path.join(f"data/topic/{self.topic}/audios", f"{item['id']}.mp3")
            if os.path.exists(audio_path):
                print(f"音频已存在: {audio_path}")
                continue
            audio_data = self._generate_audio(prompt)
                # 检查是否生成成功
            if audio_data is None:
                print(f"处理项目 {audio_path} 失败，跳过")
                return False
            # 保存音频文件
            try:
                with open(audio_path, "wb") as f:
                    f.write(audio_data)
                # 更新JSON文件，添加audio_path字段
                item['audio'] = audio_path
            except Exception as e:
                print(f"保存音频文件失败：{str(e)}")
                return False
        with open(topic_json_path, 'w', encoding='utf-8') as f:
            json.dump(topic_json, f, ensure_ascii=False, indent=2)
        with open(f"data/topic/{self.topic}/audios/.compeleted", 'w', encoding='utf-8') as f:
            f.write("done")
        return True

    def generate_video(self):
        video_path = f"data/topic/{self.topic}/video.mp4"
        if os.path.exists(video_path):
            print(f"视频已存在: {video_path}")
            return True
        topic_json_path = f"data/topic/{self.topic}/topic.json"
        with open(topic_json_path, 'r', encoding='utf-8') as f:
            topic_json = json.load(f)
        backgroud = ColorClip(size=(1080, 1920), color=(0, 0, 0)).to_ImageClip()
        image_clips = []
        audio_clips = []
        for item in topic_json:
            image_path = item["image"]
            audio_path = item["audio"]
            if not os.path.exists(image_path) or not os.path.exists(audio_path):
                print(f"视频或音频不存在: {image_path}, {audio_path}")
                return False
            audio_clip = AudioFileClip(audio_path)
            audio_clips.append(audio_clip)
            image_clip:ImageClip = ImageClip(image_path).with_duration(audio_clip.duration+0.5).with_audio(audio_clip)
            image_clips.append(image_clip.with_effects([vfx.Resize(width=1080)]))
        slided_clips = [
            CompositeVideoClip([clip.with_effects([vfx.SlideIn(0.5, "left")])])
            for clip in image_clips
        ]
        main_clip = concatenate_videoclips(slided_clips)
        # main_audio_clip = concatenate_audioclips(audio_clips)
        backgroud.with_duration(main_clip.duration)
        title_clip = TextClip(margin=(10,10),text=f"{self.topic}", duration=main_clip.duration, font="data/STKAITI.TTF", font_size=60, color='white', method='label', text_align='center', stroke_color='black', stroke_width=2)
        final_clip = CompositeVideoClip([backgroud, main_clip.with_position(('center', 'center')), title_clip.with_position(('center', 'top'))])
        final_clip.duration = main_clip.duration
        # final_clip = final_clip.with_audio(main_audio_clip)
        final_clip.write_videofile(video_path, fps=30, threads=4, codec="h264_nvenc")
        final_clip.preview()
        return True

    def run_work(self):
        print("开始生成话题")
        if not self.generate_topic_json():
            print("生成topic.json失败")
            return
        print("生成topic.json成功")

        print("开始生成图片")
        if not self.generate_images():
            print("生成图片失败")
            return
        print("生成图片成功")

        print("开始生成音频")
        if not self.generate_audio():
           print("生成音频失败")
        print("生成音频成功")

        print("开始生成视频")
        if not self.generate_video():
           print("生成视频失败")
           return
        print("生成视频成功")

    def generate_topic_json(self, max_retries=3, retry_delay=2):
        topic_path = f"data/topic/{self.topic}"
        if not os.path.exists(topic_path):
            os.makedirs(topic_path)
        json_path = os.path.join(topic_path, "topic.json")
        if os.path.exists(json_path):
            print(f"文件已存在: {json_path}")
            return True

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": self.PROMPT},
                        {"role": "user", "content": self.cailiao},
                    ],
                    response_format={
                        'type': 'json_object'
                    }
                )

                content = response.choices[0].message.content
                print(content)
                try:
                    result = json.loads(content)["response"]
                    if result and isinstance(result, list) and len(result) > 0:
                        with open(json_path,'w',encoding='utf-8') as f:
                            f.write(json.dumps(result,ensure_ascii=False,indent=2))
                        return True
                    else:
                        print(f"API返回空结果，第{attempt+1}次尝试")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                        continue
                except json.JSONDecodeError:
                    print(f"JSON解析失败，第{attempt+1}次尝试")
                    print(f"原始内容: {content[:100]}...")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                    continue

            except Exception as e:
                print(f"API请求错误: {str(e)}，第{attempt+1}次尝试")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                continue

        print("所有重试尝试都失败，返回空列表")
        return False

if __name__ == "__main__":
    topic = "如何提升自信心"
    generator = TopicGenerator(topic)
    result = generator.generate_topic_json()
    print(result)
