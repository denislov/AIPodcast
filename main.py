import asyncio
import os

from app.book_scraper import FQBookScraper, QidianBookScraper
from app.board import generate_board
from app.image import ImageProcessor
from app.audio import AudioGenerator
from app.topic import TopicGenerator
from app.tts import TTSGenerator
from app.video import VideoCreator
from app.video_end import save_output_video


async def main(book_id,platform: str,args:str):
    """运行命令行界面"""
    if platform == "QD":
        scraper = QidianBookScraper(book_id)
    elif platform == "FQ":
        scraper = FQBookScraper(book_id,args)
    else:
        print("平台错误")
        return
    if not scraper.get_book_content():
        print("获取书籍内容失败")
    success = generate_board(book_id)
    if success:
        processor = ImageProcessor()
        print("开始生成图片")
        processor.get_book_content(book_id)
        print("开始放大图片")
        processor.get_book_images(book_id)
        print("开始生成音频")
        audio_generator = AudioGenerator()
        audio_generator.create_book_audio(book_id)
        print("开始生成字幕文件")
        tts = TTSGenerator()
        await tts.create_tts(book_id, os.getcwd())
        print("开始生成视频")
        creator = VideoCreator(book_id)
        creator.create_book_video()
        save_output_video(book_id)

def topic_generate():
    """生成话题"""
    topic = "亲密关系1"
    cailiao = '''
    ●亲密关系满足的秘诀：1、欣赏你的伴侣，2、表达你的感激，3、重复上述两步。
　　人们会适应于愉悦的环境，如果你足够幸运（并且还兼备聪明和勤奋），拥有了美满的亲密关系，你会认为它是理所应当的，这是很危险的。但如果你变得懒惰，习惯于你的好运，你就会身在福中不知福。这非常不利于你们的亲密关系，所以我们给你一个特殊秘诀，如何同时感到满足、维持关系和对生活感觉良好。
　　听好了。要有义务地去注意伴侣为你付出的关爱、仁慈和慷慨。然后，每一周都要和你的伴侣分享你最欣赏的三个友善之举，无论巨细。
引自 第十四章 亲密关系的维持和修复
    '''
    generator = TopicGenerator(topic,cailiao=cailiao)
    generator.run_work()

if __name__ == "__main__":
    # asyncio.run(main("7415926990525451288",platform="FQ",args="&tab_type=7&top_tab_genre=-1&genre=0"))
    topic_generate()
