# (#01) 行車紀錄器 / 特斯拉 幫影片印上時間浮水印

使用 Python 和 OpenCV，給定起始時間或結束時間，來給行車紀錄器影片的每一幀加上時間戳記

---

## > 簡介

特斯拉內建手動保存影像功能，但是不會幫影片檔案加上時間戳印，手動加上必須下載很多軟體並具備剪片能力，新手很容易卻步。

希望透過自動化軟體來提升效率，包含上時間戳印 & 壓縮影片，加速檢舉舉證流程進行。

---
## **> 原始碼架構**

```python
import cv2
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from moviepy.editor import VideoFileClip
from proglog import ProgressBarLogger
import threading
import os

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

def compress_video(input_file, output_file, bitrate="1200k"):
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

        # 計算當前幀的時間戳
        current_time = start_time + datetime.timedelta(seconds=frame_index / fps)
        timestamp_str = current_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # 顯示到毫秒

        # 在幀上疊加時間戳
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.2
        font_color = (255, 255, 255)  # 白色字體
        thickness = 2
        position = (10, height - 20)  # 位置在左下角

        cv2.putText(frame, timestamp_str, position, font, font_scale, font_color, thickness)

        # 寫入輸出影片
        out.write(frame)

        frame_index += 1

        # 更新進度條
        progress = int(frame_index * 100 / total_frames)
        progress_var.set(progress)
        root.update_idletasks()

    # 釋放資源
    cap.release()
    out.release()

    compress_video(output_path, output_path_compressed)

    messagebox.showinfo("完成", f"處理完成！輸出檔案已儲存為：\n{output_path}")
    start_button.config(state=tk.NORMAL)

def select_video():
    video_path = filedialog.askopenfilename(title="選擇影片檔案", filetypes=[("影片檔案", "*.mp4;*.avi;*.mov")])
    if video_path:
        video_entry.delete(0, tk.END)
        video_entry.insert(0, video_path)
        file_name = (video_path.split("/"))[-1]
        try:
            start_date_ = (file_name.split("_"))[0]
            start_date = datetime.datetime.strptime(start_date_, '%Y-%m-%d')
            split_time = ((file_name.split("_"))[1]).split("-")
            start_time_ = split_time[0] + ":" + split_time[1] + ":" + split_time[2]
            time_entry.delete(0, tk.END)
            time_entry.insert(0, start_date_ + " " + start_time_)
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
root.title("影片加時間戳 v1.0 | SaferTW ")
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

```

---

## **> 歷史版本**

### v1.0

初始版本，提供最原始功能

---

---

© 2024, Powered by Zern
