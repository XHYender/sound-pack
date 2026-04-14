import os
import pyaudio
import wave
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis
import pygame

# 初始化 Pygame 混音器
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

class SoundBoardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Soundboard - 虚拟麦克风混音器")
        self.root.geometry("600x500")

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

        # 👇 新增：音量控制区域
        volume_frame = tk.Frame(top_frame)
        volume_frame.pack(side=tk.RIGHT, padx=10)
        
        tk.Label(volume_frame, text="🔊 音量:").pack(side=tk.LEFT)
        volume_slider = tk.Scale(volume_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                length=120, command=self.set_volume_realtime)
        volume_slider.set(80)  # 默认80%
        volume_slider.pack(side=tk.LEFT)
        
        self.volume_label = tk.Label(volume_frame, text="80%", width=4)
        self.volume_label.pack(side=tk.LEFT)


        # 2. 搜索框
        tk.Label(self.root, text="搜索音效:").pack(anchor=tk.W, padx=10)
        tk.Entry(self.root, textvariable=self.search_var).pack(fill=tk.X, padx=10, pady=5)

        # 3. 音效列表 (Treeview 支持分类和双击播放)
        list_frame = tk.Frame(self.root)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(list_frame, columns=("type", "duration"), show="tree", yscrollcommand=scrollbar.set)
        self.tree.heading("#0", text="音效名称")
        self.tree.heading("type", text="格式")
        self.tree.heading("duration", text="时长")

        self.tree.column("type", width=80)
        self.tree.column("duration", width=80)
        self.tree.pack(fill=tk.BOTH, expand=True)

        scrollbar.config(command=self.tree.yview)
        self.tree.bind("<Double-1>", self.play_selected)

        # 4. 状态栏和播放控制
        control_frame = tk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=10)

        self.status_label = tk.Label(control_frame, text="就绪 | 播放音效将混合到虚拟麦克风中")
        self.status_label.pack(side=tk.LEFT)

        tk.Button(control_frame, text="⏹️ 停止播放", command=self.stop_playback).pack(side=tk.RIGHT)

    def load_sound_list(self):
        """扫描文件夹，加载支持的文件"""
        self.sounds = []  # 存储 (路径, 显示名, 分类)
        for item in self.tree.get_children():
            self.tree.delete(item)

        for filename in os.listdir(self.audio_folder):
            if filename.lower().endswith(('.ogg', '.mp3')):
                path = os.path.join(self.audio_folder, filename)
                # 简单的分类逻辑：根据文件名前缀或文件夹名（这里演示按扩展名分类）
                category = "MP3文件" if filename.endswith('.mp3') else "OGG文件"
                try:
                    if filename.endswith('.mp3'):
                        audio = MP3(path)
                        duration = round(audio.info.length)
                    else:
                        audio = OggVorbis(path)
                        duration = round(audio.info.length)
                    duration_str = f"{duration // 60}:{duration % 60:02d}"
                except:
                    duration_str = "未知"

                # 插入到 Treeview
                self.tree.insert("", "end", text=filename, values=("音频", duration_str), tags=(category,))
                self.sounds.append((path, filename, category))

    def update_list(self, *args):
        """实时搜索过滤"""
        keyword = self.search_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)

        for path, filename, category in self.sounds:
            if keyword in filename.lower():
                try:
                    if filename.endswith('.mp3'):
                        audio = MP3(path)
                        duration = round(audio.info.length)
                    else:
                        audio = OggVorbis(path)
                        duration = round(audio.info.length)
                    duration_str = f"{duration // 60}:{duration % 60:02d}"
                except:
                    duration_str = "未知"
                self.tree.insert("", "end", text=filename, values=("音频", duration_str), tags=(category,))

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

    def old_play_audio(self, filepath):
        """实际的播放逻辑：混合到虚拟麦克风"""
        try:
            # 关键点：使用 Pygame 混音器播放
            # Pygame 默认输出到系统默认扬声器，但如果你将系统默认播放设备设为虚拟线缆的输出端，
            # 或者直接用 PyAudio 指定输出设备到虚拟线缆，即可实现“混入麦克风”。
            # 简单方案：让 Pygame 正常播放，同时你在 Windows 声音设置里把“扬声器”设为虚拟线缆即可。
            # 如果希望更精确，可以使用 PyAudio 直接输出到指定设备。
            
            # 这里演示最简单的调用：
            sound = pygame.mixer.Sound(filepath)
            # 👇 新增：应用当前音量
            sound.set_volume(self.get_current_volume())
            sound.play()
            # 等待播放结束
            while pygame.mixer.get_busy():
                pygame.time.wait(10)
            self.status_label.config(text="就绪")
        except Exception as e:
            print(f"播放错误: {e}")
            self.status_label.config(text="播放失败")

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