import os
import subprocess
from tqdm import tqdm


def concat_videos(video_paths,output_file):
        # 获取concat_list.txt的完整路径
    concat_list_path = os.path.join(os.getcwd(), "concat_list.txt")

    # 如果文件存在，先删除
    if os.path.exists(concat_list_path):
        os.remove(concat_list_path)

    # 将视频路径写入文件，每行前面加上"file "
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for path in video_paths:
            # 将路径转换为正确的格式：
            # 1. 替换所有反斜杠为正斜杠
            # 2. 在路径两边加上单引号，以处理可能包含空格的路径
            formatted_path = path.replace("\\", "/")
            f.write(f"file '{formatted_path}'\n")
    # 添加内存优化参数
    result = subprocess.call(
        [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            "concat_list.txt",
            "-c",
            "copy",
            "-max_muxing_queue_size",
            "9999",  # 增加复用队列大小
            "-threads",
            "1",  # 减少线程数以降低内存
            output_file,
        ]
    )
    if result == 0:
        print(f"视频合并成功，保存位置: {output_file}")
    else:
        print(f"视频合并失败，错误码: {result}")

def save_output_video(book_id):
    # 使用os.path.join合并路径
    video_dir = os.path.join(os.getcwd(), "data", "book", str(book_id), "video")
    # 设置最终保存位置
    output_file = os.path.join(
        os.getcwd(), "data", "book", str(book_id), str(book_id) + ".mp4"
    )
    # 递归遍历这个目录下的所有视频
    chatpers = [d for d in os.listdir(video_dir) if os.path.isdir(os.path.join(video_dir, d))]
    chatpers.sort(key=lambda x: int(x))
    final_videos = []
    with tqdm(total=len(chatpers), desc=f"总进度", unit="视频") as pbar:
        for dir in chatpers:
            # 读取每个章节的视频文件
            chatper_name = f"chatper_{dir}.mp4"
            chatper_files = [f for f in os.listdir(os.path.join(video_dir, dir)) if f.endswith(".mp4")]
            chatper_files.sort(key=lambda x: int(x.split(".")[0]))
            chatper_files_path = [os.path.join(video_dir, dir, f) for f in chatper_files]
            pbar.set_description(f"正在合并{chatper_name}")
            concat_videos(chatper_files_path, os.path.join(video_dir, chatper_name))
            final_videos.append(os.path.join(video_dir, chatper_name))

    print(f"最终视频合并中...")
    concat_videos(final_videos,output_file)

if __name__ == "__main__":
    save_output_video("7352550536014466073")
