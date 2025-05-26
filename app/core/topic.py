import gc
import json
import os
import random
import time
from dotenv import load_dotenv
from moviepy import AudioFileClip, ColorClip, ImageClip, CompositeVideoClip, TextClip, concatenate_videoclips,vfx
from openai import OpenAI
import requests
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from openai.types.shared_params import ResponseFormatJSONObject

from app.core.comfyui_tool import ComfyUITool

load_dotenv()

class TopicGenerator:
    def __init__(self, input_topic :str,cai_liao:str, draw_prompt_template: str = "", prompt_content: str = ""):
        self.topic = input_topic
        self.cai_liao = cai_liao
        self.draw_prompt_template = draw_prompt_template if draw_prompt_template else ""
        self.prompt_content = prompt_content if prompt_content else ""
        self.api_key = "sk-8b69f82630e14ea49260202ed152572b"
        self.base_url="https://api.deepseek.com"
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        # 初始化ComfyUITool
        url = os.getenv("COMFYUI_API_URL")
        workflow_file = 'data/nunchaku-turbo-dev.json'
        workflow_seed = 162434675638754
        output_dir = 'output'
        self.comfyui_tool = ComfyUITool(url, workflow_seed, workflow_file, output_dir)

    def _create_image(self, prompt: str):
        """用AI生成画面"""
        image = self.comfyui_tool.generate_clip(self.draw_prompt_template + prompt)
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
    
    @staticmethod
    def _generate_audio(text: str, max_retries=3):
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
        # title_clip = TextClip(margin=(10,10),text=f"{self.topic}", duration=main_clip.duration, font="data/STKAITI.TTF", font_size=60, color='white', method='label', text_align='center', stroke_color='black', stroke_width=2)
        # , title_clip.with_position(('center', 'top'))
        final_clip = CompositeVideoClip([backgroud, main_clip.with_position(('center', 'center'))])
        final_clip.duration = main_clip.duration
        # final_clip = final_clip.with_audio(main_audio_clip)
        final_clip.write_videofile(video_path, fps=30, threads=4, codec="h264_nvenc")
        # final_clip.preview()
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
                        ChatCompletionSystemMessageParam(content=self.prompt_content,role="system"),
                        ChatCompletionUserMessageParam(content=self.cai_liao,role="user"),
                    ],
                    response_format=ResponseFormatJSONObject(type="json_object")
                )

                content = response.choices[0].message.content
                print(content)
                try:
                    resp = json.loads(content)["response"]
                    if resp and isinstance(resp, list) and len(resp) > 0:
                        with open(json_path,'w',encoding='utf-8') as f:
                            f.write(json.dumps(resp, ensure_ascii=False, indent=2))
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
    generator = TopicGenerator(topic, "一些材料")
    result = generator.generate_topic_json()
    print(result)
