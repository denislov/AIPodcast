from calendar import c
import concurrent.futures
import requests
import json
import os
import base64
import time
from io import BytesIO
from PIL import Image  # 需要安装 Pillow 库: pip install Pillow
from dotenv import load_dotenv
from tqdm import tqdm  # 用于显示进度条
import gc
import subprocess
import glob

from app.comfyui_tool import ComfyUITool


class ImageProcessor:
    def __init__(self):
        # 加载环境变量
        load_dotenv(override=True)
        
        # 初始化ComfyUITool
        url = os.getenv("COMFYUI_API_URL")
        workflow_file = 'data/nunchaku-flux.1-dev.json'
        workflow_seed = 162434675638754  # workflowfile开头总的seed
        output_dir = 'output'
        self.comfyui_tool = ComfyUITool(url, workflow_seed, workflow_file, output_dir)

    def create_image(self, prompt: str):
        """用AI生成画面"""
        image = self.comfyui_tool.generate_clip(prompt)
        return image[0]
    
    def upscale_image(self, image_path: str):
        """调用高清修复"""
        try:
            path = os.path.join(os.getcwd(), image_path)
            command = [
                os.path.join(os.getcwd(), "models", "upscayl-bin.exe"),
                "-i", path,
                "-o", path,
                "-s", os.getenv("UPSCAYL_SCALE"),
                "-m", os.path.join(os.getcwd(), "models"),
                "-n", os.getenv("UPSCAYL_MODEL"),
                "-f", os.getenv("UPSCALY_FILE_TYPE"),
            ]
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            return False

    def delete_log_file(self):
        """删除log文件"""
        log_files = glob.glob("*.log")
        for log_file in log_files:
            try:
                os.remove(log_file)
            except Exception as e:
                print(f"删除日志文件失败 {log_file}: {e}")
        time.sleep(0.1)

    def save_error_message(self, error_msg: str, save_path: str):
        """保存错误信息到文件"""
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as error_file:
            error_file.write(error_msg)

    def get_book_content(self, book_id: str):
        """根据ID获取小说文件和提示词列表"""
        if os.path.exists(f"data/book/{book_id}/images/.compeleted"):
            print("任务已完成，跳过")
            return
        storyboard_dir = f"data/book/{book_id}/storyboard"

        if not os.path.exists(storyboard_dir):
            raise Exception(f"目录不存在: {storyboard_dir}")

        chapter_files = [f for f in os.listdir(storyboard_dir) if f.endswith(".json")]
        chapter_files = sorted(chapter_files, key=lambda x: int(x.split(".")[0]))
        chapter_file_paths = [os.path.join(storyboard_dir, f) for f in chapter_files]

        total_items = sum(len(json.load(open(p, "r", encoding="utf-8"))) for p in chapter_file_paths)

        with tqdm(total=total_items, desc="总进度", unit="图") as pbar:
            for chapter_file_path in chapter_file_paths:
                json_filename = os.path.basename(chapter_file_path).split(".")[0]
                
                with open(chapter_file_path, "r", encoding="utf-8") as f:
                    chapter_data = json.load(f)
                    chapter_data.sort(key=lambda x: int(x["id"]))

                json_updated = False

                for item_idx, item in enumerate(chapter_data):
                    item_id = item.get("id", f"index_{item_idx}")

                    if "lensLanguage_en" in item:
                        prompt = ",".join(item["lensLanguage_en"].split(",")[:30])
                        images_base_dir = f"data/book/{book_id}/images"
                        json_file_dir = os.path.join(images_base_dir, json_filename)
                        os.makedirs(json_file_dir, exist_ok=True)

                        image_path = os.path.join(json_file_dir, f"{item_id}.jpg")
                        error_path = os.path.join(json_file_dir, f"{item_id}.txt")

                        if os.path.exists(image_path):
                            if "image_path" not in item:
                                item["image_path"] = f"data/book/{book_id}/images/{json_filename}/{item_id}.jpg"
                                json_updated = True
                            gc.collect()
                        else:
                            retry_count = 0
                            success = False
                            error_msg = ""
                            
                            while retry_count < 3 and not success:
                                try:
                                    base64_image = self.create_image(prompt)
                                    with open(image_path, "wb") as binary_file:
                                        binary_file.write(base64_image)

                                    del base64_image
                                    gc.collect()
                                    if os.path.exists(image_path):
                                        success = True
                                        item["image_path"] = f"data/book/{book_id}/images/{json_filename}/{item_id}.jpg"
                                        json_updated = True
                                        gc.collect()
                                    else:
                                        error_msg = f"保存图片失败"
                                        retry_count += 1
                                        time.sleep(1)
                                except Exception as e:
                                    error_msg = f"生成图片失败 (尝试 {retry_count+1}/3): {str(e)}"
                                    retry_count += 1
                                    time.sleep(2)

                            if not success:
                                self.save_error_message(error_msg, error_path)
                    
                    pbar.update(1)
                    if item_idx % 10 == 0:
                        gc.collect()

                if json_updated:
                    with open(chapter_file_path, "w", encoding="utf-8") as f:
                        json.dump(chapter_data, f, ensure_ascii=False, indent=2)
                
                del chapter_data
                gc.collect()

        self.comfyui_tool.free()
        
    def upscale_image_thread(self, chapter_file_path: str, pbar):
        """高清修复线程"""
        with open(chapter_file_path, "r", encoding="utf-8") as f:
            chapter_data = json.load(f)
            chapter_data.sort(key=lambda x: int(x["id"]))
            
            for item in chapter_data:
                if "image_path" in item:
                    image_path = item["image_path"]
                    
                    if os.path.exists(image_path) and os.path.getsize(image_path) / (1024 * 1024) > 2:
                        pbar.update(1)
                        self.delete_log_file()
                        continue

                    upscale_result = self.upscale_image(image_path)
                    if upscale_result:
                        pbar.update(1)
                        self.delete_log_file()
                    else:
                        retry_count = 0
                        while retry_count < 3:
                            if self.upscale_image(image_path):
                                pbar.update(1)
                                self.delete_log_file()
                                break
                            retry_count += 1

    def get_book_images(self, book_id: str):
        """获取书籍图片并进行高清修复"""
        if os.path.exists(f"data/book/{book_id}/images/.compeleted"):
            print("高清修复任务已完成，跳过")
            return
        storyboard_dir = f"data/book/{book_id}/storyboard"
        chapter_files = [f for f in os.listdir(storyboard_dir) if f.endswith(".json")]
        chapter_files = sorted(chapter_files, key=lambda x: int(x.split(".")[0]))
        chapter_files = [f for f in chapter_files if f.endswith(".json")]
        chapter_file_paths = [os.path.join(storyboard_dir, f) for f in chapter_files]

        total_items = sum(len(json.load(open(p, "r", encoding="utf-8"))) for p in chapter_file_paths)
        
        try:
            num_threads = int(os.getenv("UPSCALE_NUM_THREADS", "1"))
        except ValueError:
            num_threads = 1

        with tqdm(total=total_items, desc="总进度", unit="图") as pbar:
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = []
                for chapter_file_path in chapter_file_paths:
                    future = executor.submit(self.upscale_image_thread, chapter_file_path, pbar)
                    futures.append(future)
                concurrent.futures.wait(futures)


if __name__ == "__main__":
    processor = ImageProcessor()
    processor.get_book_content("1043294775")
    processor.get_book_images("1043294775")
