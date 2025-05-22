import os
from dotenv import load_dotenv
from moviepy import ColorClip, CompositeVideoClip, TextClip, VideoFileClip


width, height = 720,1280

load_dotenv()

CHINESE_FONT = os.getenv("CHINESE_FONT")

video_file = r"data\book\7352550536014466073\video\0\1.mp4"

video_clip = VideoFileClip(video_file)

text = "Hello World"

text_clip = TextClip(font=CHINESE_FONT,text=text,font_size=48,size=(width,None), method='caption', color="yellow", stroke_color="black", stroke_width=2, text_align="center", bg_color=(0, 0, 0, 0), transparent=False)
text_clip = text_clip.with_position(("center",0.8), relative=True).with_duration(3)

video = CompositeVideoClip([video_clip,ColorClip, text_clip])
video.preview()
video.write_videofile("test.mp4", fps=24,codec="h264_nvenc",bitrate="10000k",threads=4)