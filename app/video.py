from uuid import uuid4, uuid5
import PIL.Image
import numpy as np
from moviepy import ImageClip, AudioFileClip, CompositeVideoClip, TextClip
from moviepy.tools import convert_to_seconds,close_all_clips
import os
import threading
from tqdm import tqdm
from dotenv import load_dotenv
import json
import concurrent.futures
import random
from PIL import Image, ImageDraw, ImageFont
import platform
import traceback

class VideoCreator:
    def __init__(self, book_id):
        self.book_id = book_id
        self._load_env_vars()
        self.json_locks = {}
        self._patch_pil_antialias()

    def _load_env_vars(self):
        """Loads environment variables."""
        load_dotenv(override=True)
        self.CHINESE_FONT = os.getenv("CHINESE_FONT")

    def _patch_pil_antialias(self):
        """Adds compatibility patch for PIL.Image.ANTIALIAS."""
        if not hasattr(PIL.Image, "ANTIALIAS"):
            PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

    def create_video_with_moving_image(
        self,
        image_path,
        audio_path,
        output_path,
        move_direction="left",
        portrait_mode=False,
        video_width=None,
        video_height=None,
        move_distance=0.1,
        move_speed=1.0,
        entrance_effect=False,
        entrance_duration=1.0,
        entrance_direction="left",
    ):
        """Creates a video with a moving image, audio, and optional subtitles."""
        try:
            if video_width is not None and video_height is not None:
                final_width, final_height = video_width, video_height
            else:
                final_width, final_height = (750, 1280) if portrait_mode else (2560, 1440)

            audio = AudioFileClip(audio_path)
            audio_duration:int = audio.duration
            image_clip = ImageClip(image_path)

            width_ratio = final_width / image_clip.w
            height_ratio = final_height / image_clip.h
            base_scale_factor = min(width_ratio, height_ratio)
            extra_scale = 1.0 + (move_speed * move_distance)
            scale_factor = base_scale_factor * 1.4 * extra_scale # Original logic maintained
            resized_image = image_clip.resized(scale_factor)

            extra_width = max(0, resized_image.w - final_width)
            extra_height = max(0, resized_image.h - final_height)
            safe_x_distance = min(resized_image.w * move_distance * move_speed, extra_width)
            safe_y_distance = min(resized_image.h * move_distance * move_speed, extra_height)

            entrance_x_offset, entrance_y_offset = 0, 0
            if entrance_effect:
                if entrance_direction == "left": entrance_x_offset = -resized_image.size[0]
                elif entrance_direction == "right": entrance_x_offset = final_width
                elif entrance_direction == "up": entrance_y_offset = -resized_image.size[1]
                elif entrance_direction == "down": entrance_y_offset = final_height

            def move_position(t):
                if entrance_effect and t < entrance_duration:
                    entrance_progress = t / entrance_duration
                    normal_start_x, normal_start_y = 0, 0
                    if move_direction == "right": normal_start_x = -safe_x_distance
                    elif move_direction == "down": normal_start_y = -safe_y_distance

                    if entrance_direction == "left":
                        return (entrance_x_offset * (1 - entrance_progress) + normal_start_x * entrance_progress, normal_start_y)
                    elif entrance_direction == "right":
                        return (entrance_x_offset * (1 - entrance_progress) + normal_start_x * entrance_progress, normal_start_y)
                    elif entrance_direction == "up":
                        return (normal_start_x, entrance_y_offset * (1 - entrance_progress) + normal_start_y * entrance_progress)
                    elif entrance_direction == "down":
                        return (normal_start_x, entrance_y_offset * (1 - entrance_progress) + normal_start_y * entrance_progress)

                adjusted_progress = 0
                if entrance_effect:
                    remaining_time = audio_duration - entrance_duration
                    if remaining_time <= 0: adjusted_progress = 0
                    else:
                        t_after_entrance = max(0, t - entrance_duration)
                        adjusted_progress = min(1.0, (t_after_entrance / remaining_time) * move_speed)
                else:
                    adjusted_progress = min(1.0, (t / audio_duration) * move_speed if audio_duration > 0 else 0)


                if move_direction == "left": return (-safe_x_distance * adjusted_progress, 0)
                elif move_direction == "right": return (-safe_x_distance * (1 - adjusted_progress), 0)
                elif move_direction == "up": return (0, -safe_y_distance * adjusted_progress)
                elif move_direction == "down": return (0, -safe_y_distance * (1 - adjusted_progress))
                return (-safe_x_distance * adjusted_progress, 0) # Default

            moving_image:ImageClip = resized_image.with_position(move_position).with_duration(audio_duration)
            final_clip_elements = [moving_image]

            # srt_path = os.path.splitext(audio_path)[0] + ".json"
            # if os.path.exists(srt_path):
            #     subtitles = json.load(open(srt_path, "r", encoding="utf-8"))
            #     if subtitles:
            #         for sub in subtitles:
            #             if len(sub['text']) > 100:
            #                 subtitles.insert(0, sub)
            #         for sub in subtitles:
            #             try:
            #                 start_time, end_time, text = sub["start"], sub["end"], sub["text"]
            #                 duration = end_time - start_time
            #                 if duration <=0: continue # Skip invalid duration subtitles
            #                 subtitle_img_clip = TextClip(text=text, font=self.CHINESE_FONT,size=(final_width,100), method = "caption",duration=duration, color="yellow", text_align="center")
            #                 subtitle_img_clip = subtitle_img_clip.with_position(("center",0.8), relative=True)
            #                 final_clip_elements.append(subtitle_img_clip.with_start(start_time))
            #             except Exception as e:
            #                 print(f"处理单个字幕时出错: {e}\n{traceback.format_exc()}")
            #                 continue
            video_composition:CompositeVideoClip = CompositeVideoClip(final_clip_elements, size=(final_width, final_height)).with_audio(audio)
            video_composition.write_videofile(
                output_path, fps=24, codec="h264_nvenc",bitrate="10000k", logger=None # Pass None to avoid moviepy's default progbar
            )

            # Close clips
            close_all_clips(locals())
            return True
        except Exception as e:
            print(f"视频生成失败 ({output_path})，错误: {e}\n{traceback.format_exc()}")
            # Ensure all closable resources are attempted to be closed in case of error
            close_all_clips(locals())
            return False
        finally: # Ensure temp files for audio are cleaned up
            if 'temp_input' in locals() and os.path.exists(temp_input):
                try: os.remove(temp_input)
                except Exception as e_rem: print(f"Failed to remove temp_input {temp_input}: {e_rem}")
            if 'temp_output' in locals() and os.path.exists(temp_output):
                try: os.remove(temp_output)
                except Exception as e_rem: print(f"Failed to remove temp_output {temp_output}: {e_rem}")

    def _update_json_with_video_path(self, chapter_file_path, item_id, video_path):
        """Updates the JSON file with the created video path."""
        lock = self.json_locks.setdefault(chapter_file_path, threading.Lock())
        with lock:
            try:
                with open(chapter_file_path, "r", encoding="utf-8") as f:
                    chapter_data = json.load(f)
                for item in chapter_data:
                    if item["id"] == item_id:
                        item["video_path"] = video_path
                        break
                with open(chapter_file_path, "w", encoding="utf-8") as f:
                    json.dump(chapter_data, f, ensure_ascii=False, indent=4)
                return True
            except Exception as e:
                print(f"更新JSON文件失败 ({chapter_file_path}): {str(e)}")
                return False

    def _process_item(self, item, chapter_file_path, pbar):
        """Processes a single item (text, image, audio) to create a video segment."""
        item_id = item["id"]
        # text = item["text"] # Text not directly used in video creation but part of item data

        chapter_name = os.path.basename(chapter_file_path).split(".")[0]
        video_dir = f"data/book/{self.book_id}/video/{chapter_name}"
        video_path = os.path.join(video_dir, f"{item_id}.mp4")
        image_path = f"data/book/{self.book_id}/images/{chapter_name}/{item_id}.jpg"
        audio_path = f"data/book/{self.book_id}/audio/{chapter_name}/{item_id}.mp3"

        os.makedirs(video_dir, exist_ok=True)

        pbar.set_description(f"处理项目 {video_path.split('/')[-2:]}")

        relative_video_path = f"video/{chapter_name}/{item_id}.mp4" # Path to store in JSON

        if os.path.exists(video_path):
            # Check if JSON needs update even if file exists
            needs_update = True
            try:
                with open(chapter_file_path, "r", encoding="utf-8") as f:
                    current_chapter_data = json.load(f)
                for current_item in current_chapter_data:
                    if current_item["id"] == item_id and current_item.get("video_path") == f"/data/book/{self.book_id}/{relative_video_path}": # Check specific path format
                        needs_update = False
                        break
            except Exception as e:
                 print(f"Error checking JSON for existing video path for {item_id}: {e}")


            if not needs_update:
                # self.logger.info(f"视频 {video_path} 已存在且JSON已更新，跳过。")
                if pbar: pbar.update(1)
                return True
            else:
                # self.logger.info(f"视频 {video_path} 已存在，但JSON需要更新或路径不匹配。")
                 # Storing the more complete relative path
                full_relative_video_path = f"/data/book/{self.book_id}/video/{chapter_name}/{item_id}.mp4"
                self._update_json_with_video_path(chapter_file_path, item_id, full_relative_video_path)
                if pbar: pbar.update(1)
                return True


        # Ensure source files exist
        if not os.path.exists(image_path):
            print(f"图片文件不存在: {image_path}，跳过项目 {chapter_name}/{item_id}")
            if pbar: pbar.update(1)
            return False
        if not os.path.exists(audio_path):
            print(f"音频文件不存在: {audio_path}，跳过项目 {chapter_name}/{item_id}")
            if pbar: pbar.update(1)
            return False

        video_created = self.create_video_with_moving_image(
            image_path=image_path,
            audio_path=audio_path,
            output_path=video_path,
            move_direction=random.choice(["left", "up", "down", "right"]),
            portrait_mode=os.getenv("PORTRAIT_MODE", "False").lower() == "true", # Read from env
            video_width=int(os.getenv("VIDEO_WIDTH", "750")),
            video_height=int(os.getenv("VIDEO_HEIGHT", "1280")),
            move_distance=float(os.getenv("MOVE_DISTANCE", "0.1")),
            move_speed=float(os.getenv("MOVE_SPEED", "1.0")),
            entrance_effect=os.getenv("ENTRANCE_EFFECT", "False").lower() == "true",
            entrance_duration=float(os.getenv("ENTRANCE_DURATION", "1.0")),
        )

        if not video_created:
            print(f"处理项目 {chapter_name}/{item_id} 的视频生成失败，跳过")
            if pbar: pbar.update(1)
            return False

        # Update JSON with the relative path for consistency
        full_relative_video_path = f"/data/book/{self.book_id}/video/{chapter_name}/{item_id}.mp4"
        if not self._update_json_with_video_path(chapter_file_path, item_id, full_relative_video_path):
            print(f"为项目 {chapter_name}/{item_id} 更新JSON失败")
            # Decide if this is a critical failure for the item processing
            # For now, we consider the video created, but JSON update failed.

        if pbar: pbar.update(1)
        return True

    def create_book_video(self):
        """Creates videos for all chapters and items in a book."""
        try:
            num_threads = int(os.getenv("VIDEO_THREADS", "1"))
        except ValueError:
            print("VIDEO_THREADS环境变量无效，将使用默认值 1")
            num_threads = 1
        num_threads = 1
        storyboard_dir = f"data/book/{self.book_id}/storyboard"
        if not os.path.exists(storyboard_dir):
            print(f"小说信息目录不存在: {storyboard_dir}")
            return

        try:
            chapter_files = [f for f in os.listdir(storyboard_dir) if f.endswith(".json")]
            # Sort by the numeric part of the filename
            chapter_files.sort(key=lambda x: int(os.path.splitext(x)[0]))
            chapter_file_paths = [os.path.join(storyboard_dir, f) for f in chapter_files]
        except Exception as e:
            print(f"读取或排序章节文件失败: {str(e)}")
            return

        total_items = 0
        items_to_process = []
        for chapter_file_path in chapter_file_paths:
            try:
                with open(chapter_file_path, "r", encoding="utf-8") as f:
                    chapter_data = json.load(f)
                    for item in chapter_data:
                        items_to_process.append((item, chapter_file_path))
                    total_items += len(chapter_data)
            except Exception as e:
                print(f"计算总项目或读取章节 {chapter_file_path} 失败: {str(e)}")
                # Continue to process other chapters if one fails to load
                continue

        if total_items == 0:
            print("没有在故事板中找到要处理的项目。")
            return

        with tqdm(total=total_items, desc=f"总进度", unit="视频") as pbar:
            if num_threads > 1:
                with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
                    futures = [
                        executor.submit(self._process_item, item_data, chap_path, pbar)
                        for item_data, chap_path in items_to_process
                    ]
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            future.result() # To catch exceptions from threads
                        except Exception as e:
                             print(f"线程中发生错误: {e}\n{traceback.format_exc()}")
            else: # Single-threaded execution for easier debugging or when threads=1
                for item_data, chap_path in items_to_process:
                    try:
                        self._process_item(item_data, chap_path, pbar)
                    except Exception as e:
                        print(f"处理项目时发生错误 (单线程): {e}\n{traceback.format_exc()}")
        print(f"书籍 {self.book_id} 的视频创建过程完成。")

# Main execution
if __name__ == "__main__":
    import traceback # For detailed error logging in __main__
    # Example: Get book_id from environment or command line argument
    book_id_to_process = os.getenv("BOOK_ID_TO_PROCESS")
    if not book_id_to_process:
        # Fallback or default if not set, e.g. the original hardcoded one or raise error
        book_id_to_process = "1043294775" # Default from original script
        print(f"BOOK_ID_TO_PROCESS 未设置，使用默认值: {book_id_to_process}")

    # Ensure PIL Antialias patch is applied globally if needed by external calls
    # Though it's also handled in the class constructor now.
    if not hasattr(PIL.Image, "ANTIALIAS"):
        PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

    creator = VideoCreator(book_id=book_id_to_process)
    creator.create_book_video()