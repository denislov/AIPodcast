import traceback
import httpx
import os
import json
from tqdm import tqdm
import asyncio

class TTSGenerator:
    def __init__(self, api_url="http://localhost:8000"):
        """初始化TTS生成器，使用FastAPI API"""
        self.api_url = api_url
        num_threads = int(os.getenv("VIDEO_THREADS", "1"))
        self.semaphore = asyncio.Semaphore(num_threads)

    async def generate_subtitle(self, audio_file, output_srt=None):
        """
        通过API将音频文件转换为高精度的 json 格式的字幕文件，并保存到指定位置。
        """
        if output_srt is None:
            base_name = os.path.splitext(audio_file)[0]
            output_srt = f"{base_name}.json"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                with open(audio_file, "rb") as f:
                    files = {"audio_file": (audio_file, f)}
                    response = await client.post(self.api_url+'/api/v1/transcribe/', files=files)
                
                response.raise_for_status()  # 检查是否有HTTP错误
                transcription = response.json().get("transcription", "")
                json_str = json.dumps(transcription, indent=4,ensure_ascii=False)
                # 简单地将转录文本写入 SRT 文件
                with open(output_srt, "w", encoding="utf-8") as json_file:
                    json_file.write(json_str)

                return output_srt

        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e}")
            return None
        except httpx.TimeoutException as e:
            print(f"Timeout error: {e}")
            return None
        except Exception as e:
            print(f"Error: {e}")
            traceback.print_exc()
            return None

    async def tts_thread(self, chapter_file_path, book_id, base_path, pbar):
        """处理单个章节的线程函数"""
        async with self.semaphore:
            with open(chapter_file_path, "r", encoding="utf-8") as f:
                chapter_data = json.load(f)
                for item in chapter_data:
                    audio_path = item["audio_path"]
                    
                    if "data/" not in audio_path:
                        audio_path = f"data/book/{book_id}/{audio_path}"
                    srt_path = audio_path.replace(".mp3", ".json")
                    if os.path.exists(srt_path):
                        pbar.update(1)
                        continue
                    audio_path = os.path.join(base_path, audio_path)
                    pbar.set_description(f"正在处理{audio_path.split('/')[-2:]}")
                    await self.generate_subtitle(audio_path, srt_path)
                    pbar.update(1)

    async def create_tts(self, book_id: str, base_path: str):
        """批量创建TTS字幕"""
        storyboard_dir = f"data/book/{book_id}/storyboard"
        if not os.path.exists(storyboard_dir):
            return

        try:
            chapter_files = [f for f in os.listdir(storyboard_dir) if f.endswith(".json")]
            chapter_files.sort(key=lambda x: int(x.split(".")[0]))
            chapter_file_paths = [os.path.join(storyboard_dir, f) for f in chapter_files]
        except Exception:
            return

        total_items = 0
        try:
            for chapter_file_path in chapter_file_paths:
                with open(chapter_file_path, "r", encoding="utf-8") as f:
                    chapter_data = json.load(f)
                    total_items += len(chapter_data)
        except Exception:
            return

        with tqdm(total=total_items, desc="总进度", unit="图") as pbar:
            tasks = [
                self.tts_thread(chapter_file_path, book_id, base_path, pbar)
                for chapter_file_path in chapter_file_paths
            ]
            await asyncio.gather(*tasks)
        with httpx.Client() as client:
            response = client.post(self.api_url+"/api/v1/free_model/")
            response.raise_for_status()


async def main():
    tts = TTSGenerator()
    await tts.create_tts("7352550536014466073", os.getcwd())

if __name__ == "__main__":
    asyncio.run(main())
