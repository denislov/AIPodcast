import os
import json
from PySide6.QtCore import QThread, Signal, Qt, QUrl
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QTextEdit, QPushButton, QProgressBar, 
                             QSplitter, QFrame, QTabWidget, QMessageBox, 
                             QSlider, QScrollArea,QGridLayout)
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from app.qtbind.topic import WorkerThread

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