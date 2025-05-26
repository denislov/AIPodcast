from PySide6.QtCore import QThread, Signal, Qt, QUrl
from app.core.topic import TopicGenerator

class WorkerThread(QThread):
    update_progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, topic, cailiao, task_type, draw_prompt_template="", prompt_content=""):
        super().__init__()
        self.topic = topic
        self.cailiao = cailiao
        self.task_type = task_type
        self.draw_prompt_template = draw_prompt_template
        self.prompt_content = prompt_content

    def run(self):
        try:
            # 创建TopicGenerator实例
            generator = TopicGenerator(self.topic, self.cailiao, 
                                      draw_prompt_template=self.draw_prompt_template,
                                      prompt_content=self.prompt_content)
            
            # 设置进度回调
            def progress_callback(message):
                self.update_progress.emit(message)
            
            generator.progress_callback = progress_callback
            
            # 根据任务类型执行不同的操作
            if self.task_type == "topic":
                generator.generate_topic_json()
                self.finished.emit(True, f"话题 '{self.topic}' 生成成功")
            elif self.task_type == "images":
                generator.generate_images()
                self.finished.emit(True, f"话题 '{self.topic}' 的图片生成成功")
            elif self.task_type == "audio":
                generator.generate_audio()
                self.finished.emit(True, f"话题 '{self.topic}' 的音频生成成功")
            elif self.task_type == "video":
                generator.generate_video()
                self.finished.emit(True, f"话题 '{self.topic}' 的视频生成成功")
            elif self.task_type == "all":
                generator.run_work()
                self.finished.emit(True, f"话题 '{self.topic}' 的所有内容生成成功")
            else:
                self.finished.emit(False, f"未知的任务类型: {self.task_type}")
        except Exception as e:
            import traceback
            error_msg = f"执行 {self.task_type} 任务时出错: {str(e)}\n{traceback.format_exc()}"
            self.update_progress.emit(error_msg)
            self.finished.emit(False, f"执行 {self.task_type} 任务时出错: {str(e)}")
