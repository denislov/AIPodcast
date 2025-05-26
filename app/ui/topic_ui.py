import os
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QLineEdit, QTextEdit, QPushButton, QProgressBar,
                               QSplitter, QFrame, QTabWidget, QMessageBox, QGridLayout,
                               QComboBox)
from PySide6.QtGui import QFont

from app.qtbind.topic import WorkerThread
from app.ui.TopicPreview import TopicPreviewWidget
from app.ui.VideoPreview import VideoPreviewWidget


class TopicUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.prompt_content = ""
        self.draw_prompt_template = ""
        self.setWindowTitle("AI Podcast 话题生成器")
        self.resize(900, 600)

        # 设置文件路径
        self.settings_file = os.path.join(os.getcwd(), "topic_settings.json")

        # 初始化UI
        self.side_tab_widget = QTabWidget()
        self.main_vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.topic_input = QLineEdit()
        self.topic_combo = QComboBox()
        self.cai_liao_input = QTextEdit()
        self.log_panel = QFrame()
        self.log_output = QTextEdit()
        self.toggle_log_button = QPushButton("隐藏日志")
        self.draw_prompt_input = QTextEdit()
        self.generate_all_button = QPushButton("生成全部")
        self.generate_topic_button = QPushButton("仅生成话题")
        self.generate_images_button = QPushButton("仅生成图片")
        self.generate_audio_button = QPushButton("仅生成音频")
        self.generate_video_button = QPushButton("仅生成视频")
        self.load_preview_button = QPushButton("加载预览")
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("就绪")
        self.topic_preview = TopicPreviewWidget()
        self.video_preview = VideoPreviewWidget()
        self.prompt_input = QTextEdit()

        self.init_ui()

        # 加载设置
        self.load_settings()
        # 加载已有话题
        self.load_existing_topics()
        self.worker_thread = None

    def init_ui(self):
        self.setWindowTitle("AI短视频生成器")
        self.setMinimumSize(900, 600)  # 增加最小尺寸以适应侧边栏

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局 (用于容纳主内容和侧边栏)
        main_h_layout = QHBoxLayout(central_widget)

        # 创建侧边选项卡

        self.side_tab_widget.setTabPosition(QTabWidget.TabPosition.West)  # 设置选项卡在左侧

        # 创建工作区面板
        workspace_panel = QWidget()
        workspace_layout = QVBoxLayout(workspace_panel)

        # 创建主垂直分割器 (用于容纳主内容区和日志区)
        workspace_layout.addWidget(self.main_vertical_splitter)

        # 创建水平分割器 (包含左侧控制面板和右侧预览面板)
        horizontal_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧控制面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # 话题输入
        topic_layout = QHBoxLayout()
        topic_label = QLabel("话题:")
        self.topic_input.setPlaceholderText("请输入话题，例如：如何提升自信心")
        topic_layout.addWidget(topic_label)
        topic_layout.addWidget(self.topic_input)
        left_layout.addLayout(topic_layout)
        
        # 话题选择
        topic_select_layout = QHBoxLayout()
        topic_select_label = QLabel("选择已有话题:")
        self.topic_combo.setMinimumWidth(200)
        self.topic_combo.currentTextChanged.connect(self.on_topic_selected)
        topic_select_layout.addWidget(topic_select_label)
        topic_select_layout.addWidget(self.topic_combo)
        left_layout.addLayout(topic_select_layout)

        # 材料输入
        cai_liao_label = QLabel("材料:")
        self.cai_liao_input.setPlaceholderText("请输入相关材料内容...")
        self.cai_liao_input.setMinimumHeight(200)
        left_layout.addWidget(cai_liao_label)
        left_layout.addWidget(self.cai_liao_input)

        # 按钮组
        buttons_layout = QGridLayout()

        self.generate_all_button.clicked.connect(lambda: self.start_generation("all"))
        buttons_layout.addWidget(self.generate_all_button, 0, 0)

        self.generate_topic_button.clicked.connect(lambda: self.start_generation("topic"))
        buttons_layout.addWidget(self.generate_topic_button, 0, 1)

        self.generate_images_button.clicked.connect(lambda: self.start_generation("images"))
        buttons_layout.addWidget(self.generate_images_button, 1, 0)

        self.generate_audio_button.clicked.connect(lambda: self.start_generation("audio"))
        buttons_layout.addWidget(self.generate_audio_button, 1, 1)

        self.generate_video_button.clicked.connect(lambda: self.start_generation("video"))
        buttons_layout.addWidget(self.generate_video_button, 2, 0)

        self.load_preview_button.clicked.connect(self.load_preview)
        buttons_layout.addWidget(self.load_preview_button, 2, 1)

        left_layout.addLayout(buttons_layout)

        # 进度条
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0)  # 设置为不确定模式
        self.progress_bar.hide()
        left_layout.addWidget(self.progress_bar)

        # 状态标签
        left_layout.addWidget(self.status_label)

        # 右侧预览面板
        right_panel = QTabWidget()

        # 话题预览标签页
        right_panel.addTab(self.topic_preview, "话题预览")

        # 视频预览标签页
        right_panel.addTab(self.video_preview, "视频预览")

        # 添加左右面板到水平分割器
        horizontal_splitter.addWidget(left_panel)
        horizontal_splitter.addWidget(right_panel)
        horizontal_splitter.setSizes([400, 600])  # 设置初始大小

        # 将水平分割器添加到主垂直分割器
        self.main_vertical_splitter.addWidget(horizontal_splitter)

        # 日志输出面板
        self.log_panel.setFrameShape(QFrame.Shape.StyledPanel)
        self.log_panel.setFrameShadow(QFrame.Shadow.Raised)
        log_layout = QVBoxLayout(self.log_panel)

        log_label = QLabel("日志输出:")
        self.log_output.setReadOnly(True)
        log_layout.addWidget(log_label)
        log_layout.addWidget(self.log_output)

        # 将日志面板添加到主垂直分割器
        self.main_vertical_splitter.addWidget(self.log_panel)

        # 设置主垂直分割器的初始大小
        self.main_vertical_splitter.setSizes([500, 100])  # 初始主内容区500，日志区100

        # 添加日志显示/隐藏按钮
        self.toggle_log_button.clicked.connect(self.toggle_log_panel)
        workspace_layout.addWidget(self.toggle_log_button)  # 将按钮添加到工作区布局

        # 将工作区面板添加到侧边选项卡
        self.side_tab_widget.addTab(workspace_panel, "工作区")

        # 添加设置界面到侧边选项卡
        self.side_tab_widget.addTab(self.create_settings_widget(), "设置界面")

        # 将侧边选项卡添加到主水平布局
        main_h_layout.addWidget(self.side_tab_widget)

    # 添加create_settings_widget方法
    def create_settings_widget(self):
        # 创建设置面板
        settings_panel = QWidget()
        settings_layout = QVBoxLayout(settings_panel)

        # 添加标题
        title_label = QLabel("TopicGenerator 参数设置")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        settings_layout.addWidget(title_label)

        # DRAW_PROMPT_TEMPLATE 设置
        draw_prompt_group = QFrame()
        draw_prompt_group.setFrameShape(QFrame.Shape.StyledPanel)
        draw_prompt_group.setFrameShadow(QFrame.Shadow.Raised)
        draw_prompt_layout = QVBoxLayout(draw_prompt_group)

        draw_prompt_label = QLabel("DRAW_PROMPT_TEMPLATE:")
        draw_prompt_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        draw_prompt_layout.addWidget(draw_prompt_label)

        draw_prompt_desc = QLabel("用于图片生成的提示词模板，会与每个条目的英文提示词拼接")
        draw_prompt_layout.addWidget(draw_prompt_desc)

        self.draw_prompt_input.setMinimumHeight(150)
        self.draw_prompt_input.setPlaceholderText("输入图片生成提示词模板...")
        draw_prompt_layout.addWidget(self.draw_prompt_input)

        settings_layout.addWidget(draw_prompt_group)

        # PROMPT 设置
        prompt_group = QFrame()
        prompt_group.setFrameShape(QFrame.Shape.StyledPanel)
        prompt_group.setFrameShadow(QFrame.Shadow.Raised)
        prompt_layout = QVBoxLayout(prompt_group)

        prompt_label = QLabel("PROMPT:")
        prompt_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        prompt_layout.addWidget(prompt_label)

        prompt_desc = QLabel("用于话题生成的系统提示词")
        prompt_layout.addWidget(prompt_desc)

        self.prompt_input.setMinimumHeight(300)
        self.prompt_input.setPlaceholderText("输入话题生成系统提示词...")
        prompt_layout.addWidget(self.prompt_input)

        settings_layout.addWidget(prompt_group)

        # 保存按钮
        save_button = QPushButton("保存设置")
        save_button.clicked.connect(self.save_settings)
        settings_layout.addWidget(save_button)

        # 添加弹性空间
        settings_layout.addStretch()

        return settings_panel

    # 添加load_settings方法
    def load_settings(self):
        # 默认设置
        self.draw_prompt_template = ""
        self.prompt_content = ""
        # 尝试从文件加载设置
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.draw_prompt_template = settings.get('draw_prompt_template', self.draw_prompt_template)
                    self.prompt_content = settings.get('prompt_content', self.prompt_content)
        except Exception as e:
            self.log_output.append(f"加载设置文件出错: {str(e)}")

        # 如果设置界面已经初始化，则更新UI
        if hasattr(self, 'draw_prompt_input') and hasattr(self, 'prompt_input'):
            self.draw_prompt_input.setPlainText(self.draw_prompt_template)
            self.prompt_input.setPlainText(self.prompt_content)

    # 添加save_settings方法
    def save_settings(self):
        # 从UI获取设置
        self.draw_prompt_template = self.draw_prompt_input.toPlainText()
        self.prompt_content = self.prompt_input.toPlainText()

        # 保存到文件
        try:
            settings = {
                'draw_prompt_template': self.draw_prompt_template,
                'prompt_content': self.prompt_content
            }
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "成功", "设置已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败: {str(e)}")

    # 添加toggle_log_panel方法
    def toggle_log_panel(self):
        if self.log_panel.isVisible():
            self.log_panel.hide()
            self.toggle_log_button.setText("显示日志")
        else:
            self.log_panel.show()
            self.toggle_log_button.setText("隐藏日志")

    # 添加start_generation方法
    def start_generation(self, task_type):
        topic = self.topic_input.text().strip()
        cai_liao = self.cai_liao_input.toPlainText().strip()

        if not topic:
            QMessageBox.warning(self, "警告", "请输入话题")
            return

        if task_type != "topic" and not os.path.exists(f"data/topic/{topic}/topic.json"):
            if QMessageBox.question(self, "确认", f"话题 '{topic}' 的JSON文件不存在，是否先生成话题?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                task_type = "topic"
            else:
                return

        # 禁用所有按钮
        self.set_buttons_enabled(False)

        # 显示进度条
        self.progress_bar.show()
        self.status_label.setText(f"正在执行: {task_type}")

        # 创建并启动工作线程
        self.worker_thread = WorkerThread(topic, cai_liao, task_type, self.draw_prompt_template, self.prompt_content)
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


    # 加载已有话题
    def load_existing_topics(self):
        self.topic_combo.clear()
        self.topic_combo.addItem("-- 请选择话题 --")
        
        topic_dir = os.path.join(os.getcwd(), "data", "topic")
        if os.path.exists(topic_dir):
            topics = [d for d in os.listdir(topic_dir) if os.path.isdir(os.path.join(topic_dir, d))]
            for topic in sorted(topics):
                self.topic_combo.addItem(topic)
    
    # 话题选择变更事件
    def on_topic_selected(self, topic_text):
        if topic_text and topic_text != "-- 请选择话题 --":
            self.topic_input.setText(topic_text)
            self.load_preview()
