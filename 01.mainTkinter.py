import cv2
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from moviepy.editor import *
from proglog import ProgressBarLogger
import threading
import subprocess
import os
import pytz


FFMPEG_BINARY = 'ffmpeg'  # Or full path like 'C:/ffmpeg/bin/ffmpeg.exe' on Windows
os.environ['FFMPEG_BINARY'] = FFMPEG_BINARY
os.environ['IMAGEIO_FFMPEG_EXE'] = FFMPEG_BINARY

class MyBarLogger(ProgressBarLogger):
    
    def callback(self, **changes):
        for (parameter, value) in changes.items():
            print ('Parameter %s is now %s' % (parameter, value))
    
    def bars_callback(self, bar, attr, value,old_value=None):      
        percentage = (value / self.bars[bar]['total']) * 100
        #print(bar,attr,percentage)
        progress = int(percentage)
        progress_var.set(progress)
        root.update_idletasks()

logger = MyBarLogger()

def get_video_creation_time(video_path):
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'format_tags=creation_time',
            '-of', 'default=noprint_wrappers=1:nokey=1', video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        creation_time = result.stdout.strip()
        if creation_time:
            try:
                # 解析 ISO 格式
                dt = datetime.datetime.fromisoformat(creation_time.replace("Z", "+00:00"))
                # 轉換到台灣時區
                dt_utc = dt.astimezone(pytz.utc)
                tz_tw = pytz.timezone('Asia/Taipei')
                dt_tw = dt_utc.astimezone(tz_tw)
                return dt_tw.strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                print("time parse error:", e)
        return None
    except Exception as e:
        print("ffprobe error:", e)
        return None

def compress_video(input_file, output_file, bitrate="1800k"):
    clip = VideoFileClip(input_file)
    clip.write_videofile(output_file, bitrate=bitrate, logger=logger, verbose=False)

def process_video(video_path, start_time_str):
    try:
        # 將起始時間字符串轉換為datetime對象
        start_time = datetime.datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        messagebox.showerror("錯誤", "起始時間格式不正確，請使用YYYY-MM-DD HH:MM:SS格式。")
        return

    # 打開檔案
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        messagebox.showerror("錯誤", "無法打開影片檔案。")
        return

    # 獲取影片屬性
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 25  # 默認幀率
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # 定義輸出影片路徑
    base, ext = os.path.splitext(video_path)
    output_path = f"{base}_timestamp{ext}"
    output_path_compressed = f"{base}_timestamped_compress{ext}"

    # 定義影片編解碼器和輸出對象
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # 根據需要更改
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_index = 0

    # 處理進度顯示
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = start_time + datetime.timedelta(seconds=frame_index / fps)
        timestamp_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_color = (255, 255, 255)
        thickness = 2
        position = (10, height - 20)

        # 動態調整 font_scale 讓字串寬度約為畫面寬度 15%
        target_width = int(width * 0.20)
        font_scale = 1.0
        (text_width, text_height), _ = cv2.getTextSize(timestamp_str, font, font_scale, thickness)
        # 以迴圈方式微調 font_scale
        while text_width < target_width:
            font_scale += 0.1
            (text_width, text_height), _ = cv2.getTextSize(timestamp_str, font, font_scale, thickness)
        while text_width > target_width and font_scale > 0.1:
            font_scale -= 0.01
            (text_width, text_height), _ = cv2.getTextSize(timestamp_str, font, font_scale, thickness)

        cv2.putText(frame, timestamp_str, position, font, font_scale, font_color, thickness)
        out.write(frame)
        frame_index += 1
        progress = int(frame_index * 100 / total_frames)
        progress_var.set(progress)
        root.update_idletasks()


    # 釋放資源
    cap.release()
    out.release()

    #compress_video(output_path, output_path_compressed)

    messagebox.showinfo("完成", f"處理完成！輸出檔案已儲存為：\n{output_path}")
    start_button.config(state=tk.NORMAL)

def select_video():
    video_path = filedialog.askopenfilename(title="選擇影片檔案", filetypes=[("影片檔案", "*.mp4;*.avi;*.mov")])
    if video_path:
        video_entry.delete(0, tk.END)
        video_entry.insert(0, video_path)
        # 先嘗試用 ffprobe 取得 creation_time
        creation_time = get_video_creation_time(video_path)
        if creation_time:
            time_entry.delete(0, tk.END)
            time_entry.insert(0, creation_time)
            return
        # 若沒抓到，再用檔案名稱猜測
        file_name = (video_path.split("/"))[-1]
        try:
            start_date_ = (file_name.split("_"))[0]
            start_date = datetime.datetime.strptime(start_date_, '%Y-%m-%d')
            split_time = ((file_name.split("_"))[1]).split("-")
            start_time_ = split_time[0] + ":" + split_time[1] + ":" + split_time[2]
            time_entry.delete(0, tk.END)
            time_entry.insert(0, start_date_ + " " + start_time_)
        except:
            # 若沒抓到，再用檔案最後修改時間
            try:
                mtime = os.path.getmtime(video_path)
                dt = datetime.datetime.fromtimestamp(mtime)
                time_entry.delete(0, tk.END)
                time_entry.insert(0, dt.strftime('%Y-%m-%d %H:%M:%S'))
            except:
                pass

def start_processing():
    video_path = video_entry.get()
    start_time_str = time_entry.get()
    if not video_path or not start_time_str:
        messagebox.showerror("錯誤", "請先選擇影片檔案並輸入起始時間。")
        return

    # 禁用開始按鈕，防止重覆點擊
    start_button.config(state=tk.DISABLED)

    # 在新線程中運行影片處理，避免阻塞GUI
    threading.Thread(target=process_video, args=(video_path, start_time_str), daemon=True).start()

def on_closing():
    if messagebox.askokcancel("退出", "確定要退出程式嗎？"):
        root.destroy()

# 創建主窗口
root = tk.Tk()
root.title("影片加時間戳 v1.3 | 安全台灣SaferTW ")
root.resizable(False, False)

# 影片檔案選擇部分
video_label = tk.Label(root, text="影片檔案：")
video_label.grid(row=0, column=0, padx=10, pady=10, sticky=tk.E)

video_entry = tk.Entry(root, width=50)
video_entry.grid(row=0, column=1, padx=10, pady=10)

browse_button = tk.Button(root, text="瀏覽...", command=select_video)
browse_button.grid(row=0, column=2, padx=10, pady=10)

# 起始時間輸入部分
time_label = tk.Label(root, text="開始時間(自動抓取檔名)\n格式 YYYY-MM-DD HH:MM:SS")
time_label.grid(row=1, column=0, padx=10, pady=10, sticky=tk.E)

time_entry = tk.Entry(root, width=50)
time_entry.grid(row=1, column=1, padx=10, pady=10)

# 開始按鈕
start_button = tk.Button(root, text="開始處理", command=start_processing)
start_button.grid(row=2, column=1, padx=10, pady=10)

# 進度條
progress_var = tk.IntVar()
progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100)
progress_bar.grid(row=3, column=0, columnspan=3, padx=10, pady=10, sticky=tk.EW)

# 設置關閉窗口的事件處理
#root.protocol("WM_DELETE_WINDOW", on_closing)

# 運行主循環
root.mainloop()
