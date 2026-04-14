import os
import threading
import tkinter as tk
from tkinter import filedialog
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis
import pygame

FILE=os.path.dirname(os.path.abspath(__file__)) #工作环境目录

# 初始化 Pygame 混音器
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

class SoundBoardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Soundboard - 虚拟麦克风混音器")
        self.root.geometry("600x500")
        self.root.iconbitmap(FILE+'/assets/dick.ico')

        # 音频路径设置
        self.audio_folder = os.path.join(os.getcwd(), "sound_pack")
        if not os.path.exists(self.audio_folder):
            os.makedirs(self.audio_folder)

        # 音量控制变量 (0.0 到 1.0)
        self.volume_var = tk.DoubleVar(value=0.8)  # 默认80%音量

        # 👇 新增：当前播放通道（用于实时控制音量）
        self.current_channel = None
        self.current_sound = None

        # 搜索变量
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.update_list)

        # 构建 UI
        self.create_widgets()
        self.load_sound_list()

    def create_widgets(self):
        # 1. 顶部工具栏
        top_frame = tk.Frame(self.root)
        top_frame.pack(pady=10, fill=tk.X)

        tk.Button(top_frame, text="📂 打开声音包文件夹", command=self.open_folder).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="➕ 添加文件", command=self.add_files).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="🔄 刷新音效列表", command=self.load_sound_list).pack(side=tk.LEFT, padx=5)

        # 音量控制区域
        volume_frame = tk.Frame(top_frame)
        volume_frame.pack(side=tk.RIGHT, padx=10)
        
        tk.Label(volume_frame, text="🔊 音量:").pack(side=tk.LEFT)
        volume_slider = tk.Scale(volume_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                length=120, command=self.set_volume_realtime)
        volume_slider.set(80)
        volume_slider.pack(side=tk.LEFT)
        
        self.volume_label = tk.Label(volume_frame, text="80%", width=4)
        self.volume_label.pack(side=tk.LEFT)

        # 2. 搜索框
        search_frame = tk.Frame(self.root)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="🔍 搜索音效:").pack(side=tk.LEFT)
        tk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 3. 音效列表（带播放按钮的滚动列表）
        list_container = tk.Frame(self.root)
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建画布和滚动条
        self.canvas = tk.Canvas(list_container, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 鼠标滚轮支持
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # 4. 状态栏和播放控制
        control_frame = tk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=10)

        self.status_label = tk.Label(control_frame, text="就绪 | 播放音效将混合到虚拟麦克风中")
        self.status_label.pack(side=tk.LEFT)

        tk.Button(control_frame, text="⏹️ 停止播放", command=self.stop_playback).pack(side=tk.RIGHT)


    def load_sound_list(self):
        """扫描文件夹，加载支持的文件，并为每个文件创建播放按钮"""
        # 清空现有内容
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.sounds = []  # 存储 (路径, 文件名)
        
        # 获取所有音频文件
        audio_files = []
        for filename in os.listdir(self.audio_folder):
            if filename.lower().endswith(('.ogg', '.mp3')):
                audio_files.append(filename)
        
        # 排序
        audio_files.sort()
        
        # 为每个文件创建一行
        for idx, filename in enumerate(audio_files):
            file_path = os.path.join(self.audio_folder, filename)
            
            # 获取时长
            try:
                if filename.endswith('.mp3'):
                    audio = MP3(file_path)
                    duration = round(audio.info.length)
                else:
                    audio = OggVorbis(file_path)
                    duration = round(audio.info.length)
                duration_str = f"{duration // 60}:{duration % 60:02d}"
            except:
                duration_str = "未知"
            
            # 创建行框架
            row_frame = tk.Frame(self.scrollable_frame)
            row_frame.pack(fill=tk.X, pady=2, padx=5)
            
            # 播放按钮
            play_btn = tk.Button(row_frame, text="▶️", width=3, 
                                command=lambda path=file_path: self.play_audio(path))
            play_btn.pack(side=tk.LEFT, padx=(0, 5))
            
            # 文件名标签
            name_label = tk.Label(row_frame, text=filename, anchor="w", width=40)
            name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # 时长标签
            duration_label = tk.Label(row_frame, text=duration_str, width=8, fg="gray")
            duration_label.pack(side=tk.RIGHT, padx=5)
            
            # 存储信息（供搜索使用）
            self.sounds.append((file_path, filename, row_frame))
        
        # 应用搜索过滤
        self.update_list()

    def update_list(self, *args):
        """实时搜索过滤"""
        keyword = self.search_var.get().lower()
        
        for file_path, filename, row_frame in self.sounds:
            if keyword in filename.lower():
                row_frame.pack(fill=tk.X, pady=2, padx=5)  # 显示
            else:
                row_frame.pack_forget()  # 隐藏

    def play_selected(self, event):
        """播放选中的音效（通过虚拟麦克风输出）"""
        selection = self.tree.selection()
        if not selection:
            return
        item = selection[0]
        filename = self.tree.item(item, "text")
        file_path = os.path.join(self.audio_folder, filename)

        if not os.path.exists(file_path):
            return

        self.status_label.config(text=f"正在播放: {filename}")
        # 在后台线程播放，避免界面卡顿
        threading.Thread(target=self._play_audio, args=(file_path,), daemon=True).start()

    def play_audio(self, filepath):
        """播放指定的音频文件"""
        self.status_label.config(text=f"正在播放: {os.path.basename(filepath)}")
        threading.Thread(target=self._play_audio, args=(filepath,), daemon=True).start()

    def _play_audio(self, filepath):
        """实际的播放逻辑：支持实时音量调整"""
        try:
            # 停止当前正在播放的声音（可选：如果你希望同时播放多个音效，去掉这个）
            if self.current_channel is not None and self.current_channel.get_busy():
                self.current_channel.stop()
            
            # 加载声音
            sound = pygame.mixer.Sound(filepath)
            self.current_sound = sound
            
            # 获取一个空闲通道并播放
            self.current_channel = sound.play()
            
            # 立即应用当前音量
            if self.current_channel is not None:
                current_vol = self.volume_var.get()
                self.current_channel.set_volume(current_vol, current_vol)
            
            self.status_label.config(text=f"正在播放: {os.path.basename(filepath)}")
            
            # 等待播放完成（不阻塞界面，用轮询）
            def check_playback():
                if self.current_channel and self.current_channel.get_busy():
                    self.root.after(100, check_playback)
                else:
                    self.status_label.config(text="就绪")
                    self.current_channel = None
                    self.current_sound = None
            
            self.root.after(100, check_playback)
            
        except Exception as e:
            print(f"播放错误: {e}")
            self.status_label.config(text="播放失败")

    def stop_playback(self):
        """停止当前播放"""
        if self.current_channel is not None:
            self.current_channel.stop()
            self.current_channel = None
            self.current_sound = None
        self.status_label.config(text="已停止")

    def open_folder(self):
        """打开声音包文件夹"""
        os.startfile(self.audio_folder)  # Windows
        # import subprocess
        # subprocess.Popen(['open', self.audio_folder]) # Mac

    def add_files(self):
        """添加新的音效文件"""
        files = filedialog.askopenfilenames(filetypes=[("Audio Files", "*.mp3 *.ogg")])
        for f in files:
            dest = os.path.join(self.audio_folder, os.path.basename(f))
            if not os.path.exists(dest):
                import shutil
                shutil.copy(f, dest)
        self.load_sound_list()

    def set_volume(self, value):
        """设置全局音量"""
        volume = float(value) / 100.0  # 0-100 转成 0.0-1.0
        pygame.mixer.music.set_volume(volume)  # 设置背景音乐音量（如果有用）
        # 注意：pygame.mixer.Sound 没有全局音量，需要存储音量值供播放时使用
        self.volume_var.set(volume)
        self.volume_label.config(text=f"{int(value)}%")

    def get_current_volume(self):
        """获取当前音量值 (0.0-1.0)"""
        return self.volume_var.get()
    
    def set_volume_realtime(self, value):
        """实时调整正在播放的声音的音量"""
        volume = float(value) / 100.0
        self.volume_var.set(volume)
        self.volume_label.config(text=f"{int(value)}%")
        
        # 👇 关键：如果有正在播放的声音，立即调整其音量
        if self.current_channel is not None and self.current_channel.get_busy():
            self.current_channel.set_volume(volume, volume)  # 左右声道音量


if __name__ == "__main__":
    root = tk.Tk()
    app = SoundBoardApp(root)
    root.mainloop()