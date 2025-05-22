import os
import sys
import json
import threading
from PySide6.QtCore import Qt, Signal, QThread, QSize
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QTextEdit, QPushButton, QProgressBar,
                               QFileDialog, QMessageBox, QTabWidget, QScrollArea, QGridLayout,
                               QSplitter, QFrame)
from PySide6.QtGui import QPixmap, QFont, QIcon

from app.topic import TopicGenerator

class WorkerThread(QThread):
    update_progress = Signal(str)
    update_status = Signal(bool, str)
    finished = Signal(bool, str)

    def __init__(self, topic, cailiao, task_type):
        super().__init__()
        self.topic = topic
        self.cailiao = cailiao
        self.task_type = task_type
        self.generator = None

    def run(self):
        try:
            self.generator = TopicGenerator(self.topic, self.cailiao)
            
            if self.task_type == "all":
                # 执行完整流程
                self.update_progress.emit("开始生成话题...")
                if not self.generator.generate_topic_json():
                    self.finished.emit(False, "生成topic.json失败")
                    return
                self.update_progress.emit("生成topic.json成功")
                
                self.update_progress.emit("开始生成图片...")
                if not self.generator.generate_images():
                    self.finished.emit(False, "生成图片失败")
                    return
                self.update_progress.emit("生成图片成功")
                
                self.update_progress.emit("开始生成音频...")
                if not self.generator.generate_audio():
                    self.finished.emit(False, "生成音频失败")
                    return
                self.update_progress.emit("生成音频成功")
                
                self.update_progress.emit("开始生成视频...")
                if not self.generator.generate_video():
                    self.finished.emit(False, "生成视频失败")
                    return
                self.update_progress.emit("生成视频成功")
                
                self.finished.emit(True, "所有任务完成")
            
            elif self.task_type == "topic":
                # 只生成话题
                self.update_progress.emit("开始生成话题...")
                result = self.generator.generate_topic_json()
                self.finished.emit(result, "生成topic.json" + ("成功" if result else "失败"))
            
            elif self.task_type == "images":
                # 只生成图片
                self.update_progress.emit("开始生成图片...")
                result = self.generator.generate_images()
                self.finished.emit(result, "生成图片" + ("成功" if result else "失败"))
            
            elif self.task_type == "audio":
                # 只生成音频
                self.update_progress.emit("开始生成音频...")
                result = self.generator.generate_audio()
                self.finished.emit(result, "生成音频" + ("成功" if result else "失败"))
            
            elif self.task_type == "video":
                # 只生成视频
                self.update_progress.emit("开始生成视频...")
                result = self.generator.generate_video()
                self.finished.emit(result, "生成视频" + ("成功" if result else "失败"))
        
        except Exception as e:
            self.finished.emit(False, f"执行过程中出错: {str(e)}")

class TopicPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        # 创建滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        # 创建内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        
        self.scroll_area.setWidget(self.content_widget)
        self.layout.addWidget(self.scroll_area)
    
    def load_topic_data(self, topic):
        # 清除现有内容
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 检查topic.json是否存在
        topic_json_path = f"data/topic/{topic}/topic.json"
        if not os.path.exists(topic_json_path):
            label = QLabel(f"找不到话题数据: {topic_json_path}")
            self.content_layout.addWidget(label)
            return
        
        try:
            with open(topic_json_path, 'r', encoding='utf-8') as f:
                topic_data = json.load(f)
            
            # 添加话题内容
            for item in topic_data:
                frame = QFrame()
                frame.setFrameShape(QFrame.StyledPanel)
                frame.setFrameShadow(QFrame.Raised)
                frame_layout = QVBoxLayout(frame)
                
                # 添加ID和文本
                id_label = QLabel(f"ID: {item['id']}")
                id_label.setFont(QFont("Arial", 10, QFont.Bold))
                frame_layout.addWidget(id_label)
                
                text_label = QLabel(f"文本: {item['text']}")
                text_label.setWordWrap(True)
                frame_layout.addWidget(text_label)
                
                # 添加中文提示词
                prompt_zh_label = QLabel(f"中文提示词: {item.get('prompt_zh', '无')}")
                prompt_zh_label.setWordWrap(True)
                frame_layout.addWidget(prompt_zh_label)
                
                # 添加英文提示词
                prompt_en_label = QLabel(f"英文提示词: {item.get('prompt_en', '无')}")
                prompt_en_label.setWordWrap(True)
                frame_layout.addWidget(prompt_en_label)
                
                # 添加图片预览(如果有)
                if 'image' in item and os.path.exists(item['image']):
                    image_label = QLabel()
                    pixmap = QPixmap(item['image'])
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        image_label.setPixmap(pixmap)
                        frame_layout.addWidget(image_label)
                
                # 添加音频控件(如果有)
                if 'audio' in item and os.path.exists(item['audio']):
                    audio_label = QLabel(f"音频文件: {item['audio']}")
                    frame_layout.addWidget(audio_label)
                    
                    audio_button = QPushButton("播放音频")
                    audio_button.setProperty("audio_path", item['audio'])
                    audio_button.clicked.connect(self.play_audio)
                    frame_layout.addWidget(audio_button)
                
                self.content_layout.addWidget(frame)
                self.content_layout.addSpacing(20)  # 添加间距
            
        except Exception as e:
            label = QLabel(f"加载话题数据出错: {str(e)}")
            self.content_layout.addWidget(label)
    
    def play_audio(self):
        sender = self.sender()
        if sender and sender.property("audio_path"):
            audio_path = sender.property("audio_path")
            # 使用系统默认播放器播放音频
            if os.path.exists(audio_path):
                os.startfile(audio_path)
            else:
                QMessageBox.warning(self, "错误", f"找不到音频文件: {audio_path}")

class VideoPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.layout = QVBoxLayout(self)
        
        self.video_label = QLabel("未加载视频")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.video_label)
        
        self.play_button = QPushButton("播放视频")
        self.play_button.clicked.connect(self.play_video)
        self.play_button.setEnabled(False)
        self.layout.addWidget(self.play_button)
        
        self.video_path = None
    
    def load_video(self, topic):
        self.video_path = f"data/topic/{topic}/video.mp4"
        if os.path.exists(self.video_path):
            self.video_label.setText(f"视频已加载: {self.video_path}")
            self.play_button.setEnabled(True)
        else:
            self.video_label.setText(f"找不到视频: {self.video_path}")
            self.play_button.setEnabled(False)
    
    def play_video(self):
        if self.video_path and os.path.exists(self.video_path):
            os.startfile(self.video_path)
        else:
            QMessageBox.warning(self, "错误", "找不到视频文件")

class TopicUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.worker_thread = None
    
    def init_ui(self):
        self.setWindowTitle("AI短视频生成器")
        self.setMinimumSize(1000, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # 话题输入
        topic_layout = QHBoxLayout()
        topic_label = QLabel("话题:")
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText("请输入话题，例如：如何提升自信心")
        topic_layout.addWidget(topic_label)
        topic_layout.addWidget(self.topic_input)
        left_layout.addLayout(topic_layout)
        
        # 材料输入
        cailiao_label = QLabel("材料:")
        self.cailiao_input = QTextEdit()
        self.cailiao_input.setPlaceholderText("请输入相关材料内容...")
        self.cailiao_input.setMinimumHeight(200)
        left_layout.addWidget(cailiao_label)
        left_layout.addWidget(self.cailiao_input)
        
        # 按钮组
        buttons_layout = QGridLayout()
        
        self.generate_all_button = QPushButton("生成全部")
        self.generate_all_button.clicked.connect(lambda: self.start_generation("all"))
        buttons_layout.addWidget(self.generate_all_button, 0, 0)
        
        self.generate_topic_button = QPushButton("仅生成话题")
        self.generate_topic_button.clicked.connect(lambda: self.start_generation("topic"))
        buttons_layout.addWidget(self.generate_topic_button, 0, 1)
        
        self.generate_images_button = QPushButton("仅生成图片")
        self.generate_images_button.clicked.connect(lambda: self.start_generation("images"))
        buttons_layout.addWidget(self.generate_images_button, 1, 0)
        
        self.generate_audio_button = QPushButton("仅生成音频")
        self.generate_audio_button.clicked.connect(lambda: self.start_generation("audio"))
        buttons_layout.addWidget(self.generate_audio_button, 1, 1)
        
        self.generate_video_button = QPushButton("仅生成视频")
        self.generate_video_button.clicked.connect(lambda: self.start_generation("video"))
        buttons_layout.addWidget(self.generate_video_button, 2, 0)
        
        self.load_preview_button = QPushButton("加载预览")
        self.load_preview_button.clicked.connect(self.load_preview)
        buttons_layout.addWidget(self.load_preview_button, 2, 1)
        
        left_layout.addLayout(buttons_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0)  # 设置为不确定模式
        self.progress_bar.hide()
        left_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        left_layout.addWidget(self.status_label)
        
        # 日志输出
        log_label = QLabel("日志输出:")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        left_layout.addWidget(log_label)
        left_layout.addWidget(self.log_output)
        
        # 右侧预览面板
        right_panel = QTabWidget()
        
        # 话题预览标签页
        self.topic_preview = TopicPreviewWidget()
        right_panel.addTab(self.topic_preview, "话题预览")
        
        # 视频预览标签页
        self.video_preview = VideoPreviewWidget()
        right_panel.addTab(self.video_preview, "视频预览")
        
        # 添加左右面板到分割器
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])  # 设置初始大小
    
    def start_generation(self, task_type):
        topic = self.topic_input.text().strip()
        cailiao = self.cailiao_input.toPlainText().strip()
        
        if not topic:
            QMessageBox.warning(self, "警告", "请输入话题")
            return
        
        if task_type != "topic" and not os.path.exists(f"data/topic/{topic}/topic.json"):
            if QMessageBox.question(self, "确认", f"话题 '{topic}' 的JSON文件不存在，是否先生成话题?", 
                                  QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                task_type = "topic"
            else:
                return
        
        # 禁用所有按钮
        self.set_buttons_enabled(False)
        
        # 显示进度条
        self.progress_bar.show()
        self.status_label.setText(f"正在执行: {task_type}")
        
        # 创建并启动工作线程
        self.worker_thread = WorkerThread(topic, cailiao, task_type)
        self.worker_thread.update_progress.connect(self.update_progress)
        self.worker_thread.finished.connect(self.on_generation_finished)
        self.worker_thread.start()
    
    def update_progress(self, message):
        self.log_output.append(message)
        # 滚动到底部
        self.log_output.verticalScrollBar().setValue(self.log_output.verticalScrollBar().maximum())
    
    def on_generation_finished(self, success, message):
        # 隐藏进度条
        self.progress_bar.hide()
        
        # 更新状态
        self.status_label.setText(message)
        self.log_output.append(message)
        
        # 启用所有按钮
        self.set_buttons_enabled(True)
        
        # 显示结果
        if success:
            QMessageBox.information(self, "成功", message)
            # 自动加载预览
            self.load_preview()
        else:
            QMessageBox.critical(self, "失败", message)
    
    def set_buttons_enabled(self, enabled):
        self.generate_all_button.setEnabled(enabled)
        self.generate_topic_button.setEnabled(enabled)
        self.generate_images_button.setEnabled(enabled)
        self.generate_audio_button.setEnabled(enabled)
        self.generate_video_button.setEnabled(enabled)
        self.load_preview_button.setEnabled(enabled)
    
    def load_preview(self):
        topic = self.topic_input.text().strip()
        if not topic:
            QMessageBox.warning(self, "警告", "请输入话题")
            return
        
        # 加载话题预览
        self.topic_preview.load_topic_data(topic)
        
        # 加载视频预览
        self.video_preview.load_video(topic)

def main():
    app = QApplication(sys.argv)
    window = TopicUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()