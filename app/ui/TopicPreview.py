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
class TopicPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # 连接信号
        self.player.durationChanged.connect(self.update_duration)
        self.player.positionChanged.connect(self.update_position)
        self.player.playbackStateChanged.connect(self.update_play_button)
        
        self.current_audio_button = None # 用于跟踪当前点击的播放按钮
    
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
                frame.setFrameShape(QFrame.Shape.StyledPanel)
                frame.setFrameShadow(QFrame.Shadow.Raised)
                frame_layout = QVBoxLayout(frame)
                
                # 添加ID和文本
                id_label = QLabel(f"ID: {item['id']}")
                id_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
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
                        pixmap = pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        image_label.setPixmap(pixmap)
                        frame_layout.addWidget(image_label)
                
                # 添加音频控件(如果有)
                if 'audio' in item and os.path.exists(item['audio']):
                    audio_label = QLabel(f"音频文件: {item['audio']}")
                    frame_layout.addWidget(audio_label)
                    
                    # 音频控制布局
                    audio_control_layout = QHBoxLayout()
                    
                    play_button = QPushButton("播放")
                    play_button.setProperty("audio_path", item['audio'])
                    play_button.clicked.connect(self.play_audio)
                    audio_control_layout.addWidget(play_button)
                    
                    progress_slider = QSlider(Qt.Orientation.Horizontal)
                    progress_slider.setRange(0, 0) # 初始范围
                    progress_slider.sliderMoved.connect(self.set_position)
                    progress_slider.setProperty("audio_path", item['audio']) # 关联路径
                    audio_control_layout.addWidget(progress_slider)
                    
                    time_label = QLabel("00:00 / 00:00")
                    time_label.setMinimumWidth(100)
                    audio_control_layout.addWidget(time_label)

                    volume_slider = QSlider(Qt.Orientation.Horizontal)
                    volume_slider.setRange(0, 100)
                    volume_slider.setValue(int(self.audio_output.volume() * 100)) # 初始音量
                    volume_slider.setToolTip("音量")
                    volume_slider.valueChanged.connect(self.set_volume)
                    volume_slider.setMaximumWidth(100)
                    audio_control_layout.addWidget(volume_slider)
                    
                    frame_layout.addLayout(audio_control_layout)

                    # 将控件存储在字典中，以便后续更新
                    play_button.setProperty("progress_slider", progress_slider)
                    play_button.setProperty("time_label", time_label)
                    
                self.content_layout.addWidget(frame)
                self.content_layout.addSpacing(20)  # 添加间距
            
        except Exception as e:
            label = QLabel(f"加载话题数据出错: {str(e)}")
            self.content_layout.addWidget(label)
    
    def play_audio(self):
        sender = self.sender()
        if sender and sender.property("audio_path"):
            audio_path = sender.property("audio_path")
            
            if self.player.source().url() == QUrl.fromLocalFile(audio_path) and self.player.playbackState() == QMediaPlayer.PlayingState:
                self.player.pause()
                sender.setText("播放")
            elif self.player.source().url() == QUrl.fromLocalFile(audio_path) and self.player.playbackState() == QMediaPlayer.PausedState:
                self.player.play()
                sender.setText("暂停")
            else:
                # 停止当前播放的音频（如果有）
                if self.player.playbackState() != QMediaPlayer.PlaybackState.StoppedState:
                    self.player.stop()
                    if self.current_audio_button:
                        self.current_audio_button.setText("播放")

                if os.path.exists(audio_path):
                    self.player.setSource(QUrl.fromLocalFile(audio_path))
                    self.player.play()
                    sender.setText("暂停")
                    self.current_audio_button = sender # 更新当前播放按钮
                else:
                    QMessageBox.warning(self, "错误", f"找不到音频文件: {audio_path}")

    def update_duration(self, duration):
        if self.current_audio_button:
            progress_slider = self.current_audio_button.property("progress_slider")
            time_label = self.current_audio_button.property("time_label")
            if progress_slider:
                progress_slider.setRange(0, duration)
            if time_label:
                self.format_time(0, duration, time_label)

    def update_position(self, position):
        if self.current_audio_button:
            progress_slider = self.current_audio_button.property("progress_slider")
            time_label = self.current_audio_button.property("time_label")
            if progress_slider and not progress_slider.isSliderDown():
                progress_slider.setValue(position)
            if time_label:
                self.format_time(position, self.player.duration(), time_label)

    def set_position(self, position):
        self.player.setPosition(position)

    def set_volume(self, volume):
        self.audio_output.setVolume(volume / 100.0)

    def format_time(self, ms_position, ms_duration, label):
        s_position = int(ms_position / 1000)
        s_duration = int(ms_duration / 1000)
        
        minutes_pos = s_position // 60
        seconds_pos = s_position % 60
        
        minutes_dur = s_duration // 60
        seconds_dur = s_duration % 60
        
        label.setText(f"{minutes_pos:02d}:{seconds_pos:02d} / {minutes_dur:02d}:{seconds_dur:02d}")

    def update_play_button(self, state):
        if self.current_audio_button:
            if state == QMediaPlayer.PlaybackState.PlayingState:
                self.current_audio_button.setText("暂停")
            elif state == QMediaPlayer.PlaybackState.PausedState:
                self.current_audio_button.setText("播放")
            elif state == QMediaPlayer.PlaybackState.StoppedState:
                self.current_audio_button.setText("播放")
                if self.current_audio_button.property("progress_slider"):
                    self.current_audio_button.property("progress_slider").setValue(0)
                if self.current_audio_button.property("time_label"):
                    self.current_audio_button.property("time_label").setText("00:00 / 00:00")

