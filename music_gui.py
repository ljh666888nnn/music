import sys
import requests
import urllib.parse
import pygame  # 保留一些可能仍需要的pygame功能
import os
import numpy as np
import json
import re
import time
import traceback
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLineEdit, QListWidget,
                           QLabel, QSlider, QListWidgetItem, QMessageBox,
                           QScrollArea, QFrame, QCheckBox, QTabWidget, 
                           QComboBox, QToolButton, QAction, QMenu)
from PyQt5.QtGui import (QIcon, QFont, QPixmap, QPainter, QColor, QLinearGradient, 
                        QPalette, QRadialGradient, QConicalGradient, QBrush, QPen)
from PyQt5.QtCore import (Qt, QTimer, QUrl, QRect, QPointF, QSize, 
                         QPropertyAnimation, QEasingCurve, QThread, pyqtSignal)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

# 主API
BASE_URL = "https://www.kuwo.cn/search/searchMusicBykeyWord"
MP3_BASE_URL = "http://www.xintuo1.cn/music/kw/"

# 备用API
BACKUP_SEARCH_URL = "https://api.music.imsyy.top/search"
BACKUP_SONG_URL = "https://api.music.imsyy.top/song/url"

VIP_VER = "1"
CLIENT = "kt"
FT = "music"
CLUSTER = "0"
STRATEGY = "2012"
ENCODING = "utf8"
RFORMAT = "json"
MOBI = "1"
ISSUBTITLE = "1"
SHOW_COPYRIGHT_OFF = "1"
RN = 20

# 常量定义
API_TIMEOUT = 15  # API请求超时时间（秒）

class VisualizerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.bars = 32  # 增加更多的频谱柱
        self.bar_values = np.zeros(self.bars)
        self.active = False
        
        # 设置动画计时器
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(50)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start()
        
        # 动画参数
        self.phase = 0
        self.waves = 3  # 波浪数量
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置渐变背景
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(26, 26, 46, 200))
        gradient.setColorAt(0.5, QColor(40, 50, 78, 200))
        gradient.setColorAt(1, QColor(26, 26, 46, 200))
        painter.fillRect(self.rect(), gradient)
        
        # 如果没有活跃数据，绘制静态波形
        if not self.active:
            self.draw_static_wave(painter)
        else:
            self.draw_bars(painter)
    
    def draw_static_wave(self, painter):
        width = self.width()
        height = self.height()
        mid_height = height / 2
        
        # 绘制多条波浪线
        for wave in range(self.waves):
            # 为每条波浪线设置不同颜色
            hue = 180 + 120 * (wave / self.waves)
            painter.setPen(QPen(QColor.fromHsv(int(hue), 200, 250, 150), 2))
            
            # 绘制波浪线
            points = []
            amplitude = 15 - wave * 3  # 振幅逐渐减小
            frequency = 0.02 + wave * 0.01  # 频率逐渐增加
            
            for x in range(0, width, 2):
                # 使用多个正弦波叠加制造更自然的波形
                y = mid_height + amplitude * np.sin(frequency * x + self.phase) * (0.8 + 0.2 * np.sin(frequency * x * 0.3))
                points.append(QPointF(x, y))
            
            # 绘制连线
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])
    
    def draw_bars(self, painter):
        width = self.width()
        height = self.height()
        bar_width = width / self.bars
        
        for i in range(self.bars):
            # 创建彩虹色渐变效果
            hue = int(250 * i / self.bars)
            # 使柱状图对称
            mirror_i = self.bars - 1 - i if i > self.bars // 2 else i
            bar_color = QColor.fromHsv(hue, 220, 250)
            
            # 创建垂直渐变
            gradient = QLinearGradient(0, height, 0, 0)
            gradient.setColorAt(0, bar_color)
            gradient.setColorAt(1, QColor.fromHsv(hue, 150, 250, 200))
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            
            # 计算柱状高度，加入一些随机波动使显示更自然
            variance = 0.1 * np.sin(self.phase * 0.2 + i * 0.1)
            bar_height = max(3, (self.bar_values[i] + variance) * height * 0.8)
            
            x = i * bar_width
            y = height - bar_height
            
            # 绘制圆角矩形
            painter.drawRoundedRect(
                int(x + bar_width * 0.1), int(y),
                int(bar_width * 0.8), int(bar_height),
                4, 4
            )
    
    def update_values(self, values=None):
        self.active = True
        if values is None:
            # 生成更自然的随机值模拟音乐可视化
            # 使用多个正弦波叠加产生接近真实频谱的效果
            new_values = np.zeros(self.bars)
            for i in range(self.bars):
                # 将频率分为低、中、高三段赋予不同特性
                if i < self.bars * 0.3:  # 低频
                    new_values[i] = 0.3 + 0.4 * np.random.rand() + 0.2 * np.sin(self.phase * 0.05)
                elif i < self.bars * 0.7:  # 中频
                    new_values[i] = 0.2 + 0.6 * np.random.rand() * (0.5 + 0.5 * np.sin(self.phase * 0.1 + i * 0.1))
                else:  # 高频
                    new_values[i] = 0.1 + 0.3 * np.random.rand() * (0.5 + 0.5 * np.sin(self.phase * 0.2 + i * 0.2))
            
            # 平滑过渡
            self.bar_values = self.bar_values * 0.7 + new_values * 0.3
        else:
            self.bar_values = values
        
        self.update()
    
    def update_animation(self):
        # 更新动画阶段
        self.phase += 0.1
        if self.phase > 2 * np.pi:
            self.phase -= 2 * np.pi
        self.update()

# 添加歌词组件
class LyricsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lyrics = []
        self.current_time = 0
        self.current_line = -1
        
        # 设置背景透明
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.setSpacing(5)
        
        self.labels = []
        for i in range(7):  # 显示7行歌词
            label = QLabel("", self)
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)
            
            # 根据位置设置不同的样式
            if i == 3:  # 当前行
                label.setStyleSheet("""
                    color: #a8dadc; 
                    font-weight: bold; 
                    font-size: 16px;
                    background-color: rgba(61, 90, 128, 0.3);
                    border-radius: 4px;
                    padding: 4px;
                """)
            else:
                # 距离中心越远，透明度越高
                opacity = 0.5 + 0.1 * (3 - abs(i - 3))
                label.setStyleSheet(f"""
                    color: rgba(224, 251, 252, {opacity});
                    font-size: {14 - abs(i - 3)}px;
                """)
            
            layout.addWidget(label)
            self.labels.append(label)
        
    def set_lyrics(self, lyrics_text):
        if not lyrics_text:
            self.show_no_lyrics()
            return
            
        try:
            # 清理和解析歌词
            self.lyrics = []
            lines = lyrics_text.strip().split("\n")
            
            for line in lines:
                match = re.match(r'\[(\d+):(\d+\.\d+)\](.*)', line)
                if match:
                    minutes, seconds, text = match.groups()
                    time_ms = int(minutes) * 60 * 1000 + float(seconds) * 1000
                    if text.strip():  # 不添加空白歌词
                        self.lyrics.append((time_ms, text.strip()))
            
            # 按时间排序
            self.lyrics.sort(key=lambda x: x[0])
            
            # 显示初始歌词
            self.current_line = -1
            self.update_display(0)
        except Exception as e:
            print(f"解析歌词出错: {e}")
            traceback.print_exc()
            self.show_no_lyrics()
    
    def show_no_lyrics(self):
        for i, label in enumerate(self.labels):
            if i == 3:
                label.setText("暂无歌词")
            else:
                label.setText("")
        self.lyrics = []
        self.current_line = -1
        
    def update_display(self, current_time_ms):
        if not self.lyrics:
            return
            
        self.current_time = current_time_ms
        
        # 找到当前应该显示的歌词行
        line_idx = -1
        for i, (time, _) in enumerate(self.lyrics):
            if time <= current_time_ms:
                line_idx = i
            else:
                break
        
        # 如果当前行没变，不需要更新
        if line_idx == self.current_line:
            return
            
        self.current_line = line_idx
        
        # 创建滚动动画效果
        for i, label in enumerate(self.labels):
            idx = self.current_line + i - 3  # 当前行显示在中间位置
            if 0 <= idx < len(self.lyrics):
                label.setText(self.lyrics[idx][1])
                
                # 当前播放行应用特殊动画效果
                if i == 3:
                    label.setStyleSheet("""
                        color: #a8dadc; 
                        font-weight: bold; 
                        font-size: 16px;
                        background-color: rgba(61, 90, 128, 0.3);
                        border-radius: 4px;
                        padding: 4px;
                    """)
                else:
                    # 距离中心越远，透明度越高
                    opacity = 0.5 + 0.1 * (3 - abs(i - 3))
                    label.setStyleSheet(f"""
                        color: rgba(224, 251, 252, {opacity});
                        font-size: {14 - abs(i - 3)}px;
                    """)
            else:
                label.setText("")

class MusicPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("炫彩音乐播放器")
        self.setMinimumSize(900, 700)
        
        # 设置应用整体样式
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a1a2e, stop:1 #16213e);
            }
            QWidget {
                color: #FFFFFF;
                font-family: 'Microsoft YaHei', Arial;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f52ba, stop:1 #0066cc);
                border-radius: 5px;
                color: white;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a75ff, stop:1 #0052cc);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #004080, stop:1 #003366);
            }
            QLineEdit {
                padding: 8px;
                background-color: rgba(40, 44, 52, 0.8);
                border: 1px solid #3d5a80;
                border-radius: 4px;
                color: white;
                font-size: 14px;
            }
            QListWidget {
                background-color: rgba(26, 26, 46, 0.7);
                border: 1px solid #3d5a80;
                border-radius: 6px;
                padding: 5px;
                font-size: 14px;
                alternate-background-color: rgba(45, 45, 65, 0.7);
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid rgba(61, 90, 128, 0.5);
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3d5a80, stop:1 #4a6fa5);
            }
            QListWidget::item:hover {
                background-color: rgba(61, 90, 128, 0.3);
            }
            QSlider {
                height: 20px;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #3d5a80;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #e0fbfc, stop:1 #98c1d9);
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #ffffff, stop:1 #a8dadc);
            }
            QLabel {
                color: #e0fbfc;
                font-size: 14px;
            }
            QCheckBox {
                color: #e0fbfc;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QTabWidget::pane {
                border: 1px solid #3d5a80;
                border-radius: 5px;
                background-color: rgba(26, 26, 46, 0.7);
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #293241, stop:1 #3d5a80);
                color: #e0fbfc;
                padding: 8px 12px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3d5a80, stop:1 #4a6fa5);
            }
            QComboBox {
                background-color: rgba(40, 44, 52, 0.8);
                border: 1px solid #3d5a80;
                border-radius: 4px;
                padding: 5px;
                color: #e0fbfc;
            }
            QComboBox::drop-down {
                width: 20px;
                border-left: 1px solid #3d5a80;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: #e0fbfc;
            }
            QToolButton:hover {
                background-color: rgba(61, 90, 128, 0.3);
            }
            QFrame {
                border-radius: 5px;
            }
        """)
        
        self.init_ui()
        self.current_page = 0
        self.total_pages = 0
        self.search_results = []
        self.current_song_id = None
        self.current_song_name = None
        self.is_playing = False
        self.use_backup_api = False
        self.song_duration = 0
        
        # 创建媒体播放器
        self.media_player = QMediaPlayer(self)
        self.media_player.setVolume(70)  # 设置默认音量为70%
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.stateChanged.connect(self.media_state_changed)
        self.media_player.mediaStatusChanged.connect(self.media_status_changed)
        
        # 创建定时器用于更新可视化效果
        self.visualizer_timer = QTimer(self)
        self.visualizer_timer.setInterval(50)  # 更快的更新频率
        self.visualizer_timer.timeout.connect(self.update_visualizer)
        
    def init_ui(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # 顶部搜索区域
        top_frame = QFrame()
        top_frame.setStyleSheet("background-color: rgba(26, 26, 46, 0.8); border-radius: 8px;")
        top_layout = QVBoxLayout(top_frame)
        
        # 搜索区域标题
        title_label = QLabel("炫彩音乐搜索")
        title_label.setStyleSheet("color: #e0fbfc; font-size: 18px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(title_label)
        
        # 搜索控制
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("请输入歌手或歌曲名")
        self.search_input.returnPressed.connect(self.search_music)
        
        # 美化搜索框
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(40, 44, 52, 0.7);
                border: 2px solid #3d5a80;
                border-radius: 20px;
                padding: 8px 15px;
                font-size: 14px;
                color: #e0fbfc;
            }
            QLineEdit:focus {
                border-color: #98c1d9;
            }
        """)
        
        self.search_btn = QPushButton("搜索")
        self.search_btn.clicked.connect(self.search_music)
        self.search_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f52ba, stop:1 #0066cc);
                border-radius: 20px;
                color: white;
                padding: 8px 25px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a75ff, stop:1 #0052cc);
            }
        """)
        
        # 添加API选择下拉框
        self.api_combo = QComboBox()
        self.api_combo.addItem("默认音源")
        self.api_combo.addItem("备用音源")
        self.api_combo.currentIndexChanged.connect(self.change_api)
        self.api_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(40, 44, 52, 0.7);
                border: 2px solid #3d5a80;
                border-radius: 15px;
                padding: 5px 10px;
                min-width: 120px;
                color: #e0fbfc;
            }
            QComboBox::drop-down {
                border: none;
                border-left: 1px solid #3d5a80;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                background-color: rgba(26, 26, 46, 0.9);
                border: 1px solid #3d5a80;
                selection-background-color: #4a6fa5;
                color: #e0fbfc;
            }
        """)
        
        search_layout.addWidget(self.search_input, 4)
        search_layout.addWidget(self.search_btn, 1)
        search_layout.addWidget(self.api_combo, 1)
        top_layout.addLayout(search_layout)
        
        main_layout.addWidget(top_frame)
        
        # 创建内容区选项卡
        content_tabs = QTabWidget()
        content_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3d5a80;
                border-radius: 8px;
                background-color: rgba(26, 26, 46, 0.7);
            }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #293241, stop:1 #3d5a80);
                color: #e0fbfc;
                padding: 10px 15px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3d5a80, stop:1 #4a6fa5);
            }
        """)
        
        # 歌曲列表标签页
        song_list_tab = QWidget()
        song_list_layout = QVBoxLayout(song_list_tab)
        
        # 歌曲列表
        self.song_list = QListWidget()
        self.song_list.itemDoubleClicked.connect(self.play_selected_song)
        self.song_list.setAlternatingRowColors(True)
        song_list_layout.addWidget(self.song_list)
        
        # 分页控制
        page_layout = QHBoxLayout()
        self.prev_page_btn = QPushButton("上一页")
        self.prev_page_btn.clicked.connect(self.prev_page)
        self.page_info = QLabel("第 0/0 页")
        self.page_info.setAlignment(Qt.AlignCenter)
        self.next_page_btn = QPushButton("下一页")
        self.next_page_btn.clicked.connect(self.next_page)
        
        page_layout.addStretch()
        page_layout.addWidget(self.prev_page_btn)
        page_layout.addWidget(self.page_info)
        page_layout.addWidget(self.next_page_btn)
        page_layout.addStretch()
        
        song_list_layout.addLayout(page_layout)
        
        # 播放列表标签页
        playlist_tab = QWidget()
        playlist_layout = QVBoxLayout(playlist_tab)
        playlist_layout.addWidget(QLabel("您的播放列表将在这里显示"))
        # 这里可以添加播放列表功能的实现
        
        # 收藏标签页
        favorites_tab = QWidget()
        favorites_layout = QVBoxLayout(favorites_tab)
        favorites_layout.addWidget(QLabel("您收藏的歌曲将在这里显示"))
        # 这里可以添加收藏功能的实现
        
        # 添加标签页
        content_tabs.addTab(song_list_tab, "搜索结果")
        content_tabs.addTab(playlist_tab, "播放列表")
        content_tabs.addTab(favorites_tab, "我的收藏")
        
        main_layout.addWidget(content_tabs, 3)  # 占用较大空间
        
        # 播放器控制区域
        player_frame = QFrame()
        player_frame.setStyleSheet("background-color: rgba(26, 26, 46, 0.8); border-radius: 8px;")
        player_layout = QVBoxLayout(player_frame)
        
        # 在播放控制区域上方添加可视化组件
        self.visualizer = VisualizerWidget()
        self.visualizer.setMinimumHeight(100)
        self.visualizer.setStyleSheet("background-color: transparent;")
        player_layout.addWidget(self.visualizer)
        
        # 在可视化组件和播放控制之间添加歌词显示
        self.lyrics_widget = LyricsWidget()
        self.lyrics_frame = QFrame()
        self.lyrics_frame.setFrameShape(QFrame.StyledPanel)
        self.lyrics_frame.setFixedHeight(180)
        self.lyrics_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(26, 26, 46, 0.5);
                border-radius: 8px;
                border: 1px solid #3d5a80;
            }
        """)
        
        lyrics_layout = QVBoxLayout(self.lyrics_frame)
        lyrics_layout.addWidget(self.lyrics_widget)
        
        player_layout.addWidget(self.lyrics_frame)
        
        # 当前播放歌曲
        self.now_playing = QLabel("当前未播放任何歌曲")
        self.now_playing.setAlignment(Qt.AlignCenter)
        self.now_playing.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        self.now_playing.setStyleSheet("color: #a8dadc; margin: 5px 0;")
        player_layout.addWidget(self.now_playing)
        
        # 进度条
        progress_frame = QFrame()
        progress_frame.setStyleSheet("background-color: transparent; border: none;")
        progress_layout = QHBoxLayout(progress_frame)
        progress_layout.setContentsMargins(10, 5, 10, 5)
        
        self.time_label = QLabel("00:00")
        self.time_label.setStyleSheet("color: #a8dadc; font-size: 12px;")
        self.progress_bar = QSlider(Qt.Horizontal)
        self.progress_bar.setEnabled(False)
        self.progress_bar.sliderMoved.connect(self.set_position)
        self.progress_bar.sliderPressed.connect(self.slider_pressed)
        self.progress_bar.sliderReleased.connect(self.slider_released)
        self.duration_label = QLabel("00:00")
        self.duration_label.setStyleSheet("color: #a8dadc; font-size: 12px;")
        
        progress_layout.addWidget(self.time_label)
        progress_layout.addWidget(self.progress_bar, 8)
        progress_layout.addWidget(self.duration_label)
        player_layout.addWidget(progress_frame)
        
        # 播放控制按钮
        control_frame = QFrame()
        control_frame.setStyleSheet("background-color: transparent; border: none;")
        control_layout = QHBoxLayout(control_frame)
        
        # 音量控制
        volume_layout = QHBoxLayout()
        volume_icon = QLabel("🔊")
        volume_icon.setStyleSheet("color: #a8dadc; font-size: 16px;")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)  # 默认音量70%
        self.volume_slider.valueChanged.connect(self.set_volume)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #3d5a80;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #e0fbfc;
                width: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
        """)
        
        volume_layout.addWidget(volume_icon)
        volume_layout.addWidget(self.volume_slider)
        
        # 播放控制按钮
        self.prev_btn = QPushButton("⏮")
        self.play_btn = QPushButton("▶")
        self.next_btn = QPushButton("⏭")
        self.stop_btn = QPushButton("⏹")
        self.download_btn = QPushButton("💾")
        
        self.prev_btn.clicked.connect(self.play_previous)
        self.play_btn.clicked.connect(self.toggle_play)
        self.next_btn.clicked.connect(self.play_next)
        self.stop_btn.clicked.connect(self.stop_music)
        self.download_btn.clicked.connect(self.download_current_song)
        self.download_btn.setEnabled(False)
        
        # 设置按钮样式
        for btn in [self.prev_btn, self.play_btn, self.next_btn, self.stop_btn, self.download_btn]:
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3d5a80;
                    border-radius: 20px;
                    color: white;
                    font-size: 16px;
                    font-weight: bold;
                    border: none;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: #4a6fa5;
                }
                QPushButton:pressed {
                    background-color: #293241;
                }
                QPushButton:disabled {
                    background-color: #293241;
                    color: #7d8597;
                }
            """)
        
        control_layout.addLayout(volume_layout)
        control_layout.addStretch()
        control_layout.addWidget(self.prev_btn)
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.next_btn)
        control_layout.addStretch()
        control_layout.addWidget(self.download_btn)
        
        player_layout.addWidget(control_frame)
        
        main_layout.addWidget(player_frame, 2)  # 占用较小空间
    
    def change_api(self, index):
        self.use_backup_api = (index == 1)
        source_name = "备用音源" if self.use_backup_api else "默认音源"
        QMessageBox.information(self, "音源切换", f"已切换到{source_name}，请重新搜索")
    
    def search_music(self):
        search_term = self.search_input.text().strip()
        if not search_term:
            QMessageBox.warning(self, "提示", "请输入搜索内容")
            return
            
        self.current_page = 0
        self.load_page()
    
    def load_page(self):
        search_term = self.search_input.text().strip()
        
        try:
            if self.use_backup_api:
                self.load_from_backup_api(search_term)
            else:
                self.load_from_main_api(search_term)
        except Exception as e:
            QMessageBox.critical(self, "搜索失败", f"错误: {str(e)}\n请尝试切换API或稍后重试")
    
    def load_from_main_api(self, search_term):
        url = self.build_url(search_term, self.current_page)
        
        try:
            # 添加请求头
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "http://www.kuwo.cn/"
            }
            
            print(f"搜索请求: {url}")
            response = requests.get(url, headers=headers, timeout=API_TIMEOUT).json()
            
            if "abslist" not in response or "TOTAL" not in response:
                raise Exception("API返回数据格式不正确")
                
            self.total_pages = (int(response["TOTAL"]) + 19) // 20
            self.search_results = response["abslist"]
            
            print(f"搜索结果: 找到 {response['TOTAL']} 首歌曲")
            
            # 更新页码信息
            self.page_info.setText(f"第 {self.current_page + 1}/{self.total_pages} 页")
            
            # 启用/禁用分页按钮
            self.prev_page_btn.setEnabled(self.current_page > 0)
            self.next_page_btn.setEnabled(self.current_page < self.total_pages - 1)
            
            # 更新歌曲列表
            self.update_song_list()
        except requests.exceptions.Timeout:
            print("API请求超时")
            QMessageBox.critical(self, "搜索失败", f"主API请求超时，请检查网络连接或尝试切换到备用API")
        except Exception as e:
            print(f"API请求错误: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(self, "搜索失败", f"主API搜索失败: {str(e)}\n请尝试切换到备用API")
    
    def load_from_backup_api(self, search_term):
        params = {
            "keywords": search_term,
            "limit": 20,
            "offset": self.current_page * 20
        }
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json"
            }
            
            print(f"备用API搜索请求: {BACKUP_SEARCH_URL}，参数: {params}")
            response = requests.get(BACKUP_SEARCH_URL, params=params, headers=headers, timeout=API_TIMEOUT).json()
            
            if response["code"] != 200:
                raise Exception(f"备用API返回错误: {response.get('msg', '未知错误')}")
            
            # 处理搜索结果
            self.search_results = []
            for item in response["result"]["songs"]:
                # 转换为与主API相同的格式
                self.search_results.append({
                    "NAME": item["name"],
                    "ARTIST": item["artists"][0]["name"],
                    "ALBUM": item["album"]["name"],
                    "DC_TARGETID": str(item["id"]),  # 使用歌曲ID
                    "API_TYPE": "backup"  # 标记为备用API
                })
            
            # 计算总页数
            total_count = response["result"]["songCount"]
            self.total_pages = (total_count + 19) // 20
            
            print(f"备用API搜索结果: 找到 {total_count} 首歌曲")
            
            # 更新页码信息
            self.page_info.setText(f"第 {self.current_page + 1}/{self.total_pages} 页")
            
            # 启用/禁用分页按钮
            self.prev_page_btn.setEnabled(self.current_page > 0)
            self.next_page_btn.setEnabled(self.current_page < self.total_pages - 1)
            
            # 更新歌曲列表
            self.update_song_list()
        except requests.exceptions.Timeout:
            print("备用API请求超时")
            QMessageBox.critical(self, "搜索失败", f"备用API请求超时，请检查网络连接或尝试使用主API")
        except Exception as e:
            print(f"备用API请求错误: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(self, "搜索失败", f"备用API搜索失败: {str(e)}")
    
    def update_song_list(self):
        self.song_list.clear()
        for item in self.search_results:
            # 添加更多信息，帮助用户选择歌曲
            artist = item.get("ARTIST", "未知歌手")
            album = item.get("ALBUM", "")
            album_text = f" - {album}" if album else ""
            
            list_item = QListWidgetItem(f'{item["NAME"]} - {artist}{album_text}')
            list_item.setData(Qt.UserRole, item["DC_TARGETID"])
            self.song_list.addItem(list_item)
    
    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_page()
    
    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.load_page()
    
    def play_selected_song(self, item):
        song_id = item.data(Qt.UserRole)
        song_name = item.text()
        
        # 检查选中的歌曲是否来自备用API
        selected_item = None
        for result in self.search_results:
            if result["DC_TARGETID"] == song_id:
                selected_item = result
                break
        
        if selected_item and selected_item.get("API_TYPE") == "backup":
            self.stream_from_backup_api(song_id, song_name)
        else:
            self.stream_from_main_api(song_id, song_name)
    
    def stream_from_main_api(self, song_id, song_name):
        self.current_song_id = song_id
        self.current_song_name = song_name
        
        try:
            # 获取真实的MP3 URL
            mp3_url = MP3_BASE_URL + song_id
            
            # 添加浏览器请求头
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "http://www.kuwo.cn/",
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive"
            }
            
            print(f"请求资源信息: {mp3_url}")
            response = requests.get(mp3_url, headers=headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                raise Exception(f"服务器返回错误代码: {response.status_code}")
            
            # 从响应中提取真正的MP3 URL
            real_mp3_url = response.text.strip()
            print(f"获取到真正的音乐链接: {real_mp3_url}")
            
            # 启用下载按钮
            self.download_btn.setEnabled(True)
            
            # 使用QMediaPlayer直接播放URL
            self.media_player.setMedia(QMediaContent(QUrl(real_mp3_url)))
            self.media_player.play()
            
            # 更新播放状态
            self.now_playing.setText(f"正在播放: {song_name}")
            self.play_btn.setText("⏸")
            self.is_playing = True
            
            # 开始更新可视化
            self.visualizer_timer.start()
            
            # 尝试获取歌词
            self.fetch_lyrics(song_id)
                
        except Exception as e:
            print(f"播放失败: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(self, "播放失败", f"无法播放此音乐: {str(e)}\n请尝试其他歌曲")
    
    def stream_from_backup_api(self, song_id, song_name):
        self.current_song_id = song_id
        self.current_song_name = song_name
        
        try:
            # 获取歌曲URL
            params = {"id": song_id}
            print(f"请求备用API获取歌曲URL: {BACKUP_SONG_URL}?id={song_id}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json"
            }
            
            response = requests.get(BACKUP_SONG_URL, params=params, headers=headers, timeout=API_TIMEOUT).json()
            
            if response["code"] != 200:
                raise Exception(f"获取歌曲URL失败: {response.get('msg', '未知错误')}")
            
            # 获取音乐URL
            if not response["data"] or len(response["data"]) == 0:
                raise Exception("未找到音乐资源")
                
            music_url = response["data"][0]["url"]
            if not music_url:
                raise Exception("此歌曲无法播放，可能需要VIP或版权受限")
            
            print(f"获取到音乐URL: {music_url}")
            
            # 启用下载按钮
            self.download_btn.setEnabled(True)
            
            # 使用QMediaPlayer直接播放URL
            self.media_player.setMedia(QMediaContent(QUrl(music_url)))
            self.media_player.play()
            
            # 更新播放状态
            self.now_playing.setText(f"正在播放: {song_name}")
            self.play_btn.setText("⏸")
            self.is_playing = True
            
            # 开始更新可视化
            self.visualizer_timer.start()
            
            # 尝试获取歌词
            self.fetch_lyrics_from_backup(song_id)
                
        except Exception as e:
            print(f"备用API播放失败: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(self, "播放失败", f"备用API播放失败: {str(e)}\n请尝试其他歌曲")
    
    def toggle_play(self):
        if self.current_song_id is None:
            return
            
        try:
            if self.is_playing:
                self.media_player.pause()
                self.play_btn.setText("▶")
                self.is_playing = False
                self.visualizer_timer.stop()
            else:
                self.media_player.play()
                self.play_btn.setText("⏸")
                self.is_playing = True
                self.visualizer_timer.start()
        except Exception as e:
            print(f"切换播放状态出错: {str(e)}")
            traceback.print_exc()
            QMessageBox.warning(self, "播放错误", f"切换播放状态失败: {str(e)}")
    
    def stop_music(self):
        if self.current_song_id is not None:
            try:
                self.media_player.stop()
                self.is_playing = False
                self.play_btn.setText("▶")
                self.visualizer_timer.stop()
                self.progress_bar.setValue(0)
                self.time_label.setText("00:00")
                self.lyrics_widget.show_no_lyrics()
                # 不禁用下载按钮，允许用户在停止后仍可下载
            except Exception as e:
                print(f"停止播放出错: {str(e)}")
                traceback.print_exc()
    
    def position_changed(self, position):
        # 更新进度条和时间显示
        self.progress_bar.setValue(position)
        self.time_label.setText(self.format_time(position // 1000))
        
        # 更新歌词显示
        self.lyrics_widget.update_display(position)
    
    def duration_changed(self, duration):
        # 当歌曲总时长改变时
        self.progress_bar.setRange(0, duration)
        self.song_duration = duration
        self.duration_label.setText(self.format_time(duration // 1000))
    
    def media_state_changed(self, state):
        # 当媒体播放状态改变时
        if state == QMediaPlayer.PlayingState:
            self.play_btn.setText("⏸")
            self.is_playing = True
        else:
            self.play_btn.setText("▶")
            self.is_playing = False
            
            # 如果媒体停止，停止可视化更新
            if state == QMediaPlayer.StoppedState:
                self.visualizer_timer.stop()
    
    def media_status_changed(self, status):
        # 当媒体状态改变时
        if status == QMediaPlayer.EndOfMedia:
            # 播放结束，自动播放下一首
            self.play_next()
    
    def slider_pressed(self):
        # 用户按下进度条时暂停更新
        self.media_player.pause()
    
    def slider_released(self):
        # 用户释放进度条后重新播放
        self.media_player.setPosition(self.progress_bar.value())
        if self.is_playing:
            self.media_player.play()
    
    def set_position(self, position):
        # 当用户拖动进度条时，设置播放位置
        self.media_player.setPosition(position)
    
    def set_volume(self, volume):
        # 设置音量
        self.media_player.setVolume(volume)
        
    def play_previous(self):
        # 播放上一首歌曲
        # 这里可以实现播放历史功能
        QMessageBox.information(self, "提示", "播放上一首功能即将开发")
        
    def play_next(self):
        # 播放下一首歌曲
        # 这里可以实现自动播放下一首功能
        QMessageBox.information(self, "提示", "播放下一首功能即将开发")
    
    def format_time(self, seconds):
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def build_url(self, search, pn):
        search_encoded = urllib.parse.quote(search)
        return f"{BASE_URL}?vipver={VIP_VER}&client={CLIENT}&ft={FT}&cluster={CLUSTER}&strategy={STRATEGY}&encoding={ENCODING}&rformat={RFORMAT}&mobi={MOBI}&issubtitle={ISSUBTITLE}&show_copyright_off={SHOW_COPYRIGHT_OFF}&pn={pn}&rn={RN}&all={search_encoded}"
    
    def update_visualizer(self):
        if self.is_playing:
            try:
                self.visualizer.update_values()
            except Exception as e:
                print(f"更新可视化效果出错: {str(e)}")
                traceback.print_exc()
    
    def download_current_song(self):
        if self.current_song_id is None:
            return
            
        # 检查当前歌曲是哪个API的
        for result in self.search_results:
            if result["DC_TARGETID"] == self.current_song_id:
                if result.get("API_TYPE") == "backup":
                    self.download_from_backup_api()
                    return
                break
        
        try:
            # 创建downloads文件夹（如果不存在）
            if not os.path.exists("downloads"):
                os.makedirs("downloads")
            
            # 使用与原始music.py相同的方式获取音乐
            mp3_url = MP3_BASE_URL + self.current_song_id
            
            # 添加浏览器请求头
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "http://www.kuwo.cn/",
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive"
            }
            
            print(f"开始请求资源信息: {mp3_url}")
            # 获取MP3信息
            response = requests.get(mp3_url, headers=headers, timeout=API_TIMEOUT)
            
            if response.status_code != 200:
                raise Exception(f"服务器返回错误代码: {response.status_code}")
            
            # 从响应中提取真正的MP3 URL
            real_mp3_url = response.text.strip()
            print(f"获取到真正的下载链接: {real_mp3_url}")
            
            # 获取真正的MP3文件
            mp3_response = requests.get(real_mp3_url, headers=headers, timeout=API_TIMEOUT)
            if mp3_response.status_code != 200:
                raise Exception(f"下载MP3文件失败，状态码: {mp3_response.status_code}")
                
            print(f"下载完成，内容长度: {len(mp3_response.content)} 字节")
            
            # 从歌曲名和歌手名提取信息
            parts = self.current_song_name.split(' - ', 1)
            song_title = parts[0]
            artist = parts[1].split(' - ')[0] if ' - ' in parts[1] else parts[1]
            
            # 保存文件，使用更易辨别的命名方式
            safe_song_name = f"{artist} - {song_title}.mp3"
            safe_song_name = "".join(c for c in safe_song_name if c.isalnum() or c in (" ", ".", "_", "-")).rstrip()
            target_path = os.path.join("downloads", safe_song_name)
            
            # 直接保存文件
            with open(target_path, "wb") as file:
                file.write(mp3_response.content)
            
            QMessageBox.information(self, "下载成功", f"歌曲已保存到 {target_path}")
                
        except requests.exceptions.Timeout:
            print("下载超时")
            QMessageBox.critical(self, "下载失败", f"下载歌曲超时，请检查网络连接后重试")
        except Exception as e:
            print(f"下载失败: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(self, "下载失败", f"错误: {str(e)}\n请尝试其他歌曲")
    
    def download_from_backup_api(self):
        try:
            # 创建downloads文件夹
            if not os.path.exists("downloads"):
                os.makedirs("downloads")
            
            # 获取歌曲URL
            params = {"id": self.current_song_id}
            print(f"请求备用API获取歌曲URL: {BACKUP_SONG_URL}?id={self.current_song_id}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json"
            }
            
            response = requests.get(BACKUP_SONG_URL, params=params, headers=headers, timeout=API_TIMEOUT).json()
            
            if response["code"] != 200:
                raise Exception(f"获取歌曲URL失败: {response.get('msg', '未知错误')}")
            
            # 获取音乐URL
            if not response["data"] or len(response["data"]) == 0:
                raise Exception("未找到音乐资源")
                
            music_url = response["data"][0]["url"]
            if not music_url:
                raise Exception("此歌曲无法下载，可能需要VIP或版权受限")
            
            print(f"获取到音乐URL: {music_url}")
            
            # 下载歌曲，添加请求头
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Referer": "https://music.163.com/"
            }
            
            print("开始下载音乐文件...")
            music_response = requests.get(music_url, headers=headers, timeout=API_TIMEOUT)
            
            if music_response.status_code != 200:
                raise Exception(f"下载失败，状态码: {music_response.status_code}")
                
            print(f"下载完成，内容长度: {len(music_response.content)} 字节")
            
            # 从歌曲名提取信息
            parts = self.current_song_name.split(' - ', 1)
            song_title = parts[0]
            artist = parts[1].split(' - ')[0] if ' - ' in parts[1] else parts[1]
            
            # 保存文件，使用更易辨别的命名方式
            safe_song_name = f"{artist} - {song_title}.mp3"
            safe_song_name = "".join(c for c in safe_song_name if c.isalnum() or c in (" ", ".", "_", "-")).rstrip()
            target_path = os.path.join("downloads", safe_song_name)
            
            # 保存文件
            with open(target_path, "wb") as file:
                file.write(music_response.content)
                
            print(f"文件已保存: {target_path}")
            
            QMessageBox.information(self, "下载成功", f"歌曲已保存到 {target_path}")
                
        except requests.exceptions.Timeout:
            print("备用API下载超时")
            QMessageBox.critical(self, "下载失败", f"下载歌曲超时，请检查网络连接后重试")      
        except Exception as e:
            print(f"备用API下载失败: {str(e)}")
            traceback.print_exc()
            QMessageBox.critical(self, "下载失败", f"错误: {str(e)}\n请尝试其他歌曲")
    
    def fetch_lyrics(self, song_id):
        try:
            # 构造歌词API URL
            lyrics_url = f"http://m.kuwo.cn/newh5/singles/songinfoandlrc?musicId={song_id}"
            
            # 发送请求
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = requests.get(lyrics_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "lrclist" in data["data"]:
                    # 构建LRC格式歌词
                    lrc_text = ""
                    for item in data["data"]["lrclist"]:
                        minute = int(float(item["time"]) // 60)
                        second = float(item["time"]) % 60
                        lrc_text += f"[{minute:02d}:{second:06.3f}]{item['lineLyric']}\n"
                    
                    # 设置歌词
                    self.lyrics_widget.set_lyrics(lrc_text)
                    return
            
            # 如果没有找到歌词或者请求失败
            self.lyrics_widget.show_no_lyrics()
        except Exception as e:
            print(f"获取歌词出错: {e}")
            self.lyrics_widget.show_no_lyrics()
    
    def fetch_lyrics_from_backup(self, song_id):
        try:
            # 获取歌词
            lyrics_url = f"https://api.music.imsyy.top/lyric?id={song_id}"
            response = requests.get(lyrics_url).json()
            
            if response["code"] != 200:
                self.lyrics_widget.show_no_lyrics()
                return
            
            if "lrc" in response and "lyric" in response["lrc"]:
                # 设置歌词
                self.lyrics_widget.set_lyrics(response["lrc"]["lyric"])
            else:
                self.lyrics_widget.show_no_lyrics()
                
        except Exception as e:
            print(f"获取歌词出错: {e}")
            self.lyrics_widget.show_no_lyrics()
    
    # 重写closeEvent以确保程序退出前清理资源
    def closeEvent(self, event):
        try:
            if pygame.mixer.get_init():
                pygame.mixer.quit()
            
            # 停止所有计时器
            self.visualizer_timer.stop()
            
            # 删除临时音乐文件
            for filename in os.listdir('.'):
                if filename.endswith('.mp3') and os.path.isfile(filename):
                    try:
                        os.remove(filename)
                        print(f"已删除临时文件: {filename}")
                    except:
                        pass
                        
        except Exception as e:
            print(f"程序关闭时出错: {str(e)}")
            traceback.print_exc()
            
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle('Fusion')
    
    # 适用于高DPI显示
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    player = MusicPlayer()
    player.show()
    sys.exit(app.exec_()) 