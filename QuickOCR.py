"""
快捷OCR截图工具 - 轻量版
Python 3.12
所有信息统一在界面状态栏显示，无终端输出
"""

""""
test
"""

import tkinter as tk
from tkinter import messagebox
from PIL import Image
import pyautogui
import keyboard
import numpy as np
import threading
import sys
import os
import traceback
import onnxruntime
import rapidocr_onnxruntime

# ⚡使用RapidOCR，轻量快速
from rapidocr_onnxruntime import RapidOCR

# 全局单例，确保只初始化一次
_OCR_INSTANCE = None
_OCR_LOCK = threading.Lock()

def get_ocr_instance():
    global _OCR_INSTANCE
    if _OCR_INSTANCE is None:
        with _OCR_LOCK:
            if _OCR_INSTANCE is None:
                _OCR_INSTANCE = RapidOCR(
                    det_db_thresh=0.3,
                    det_db_box_thresh=0.5,
                    use_cuda=False,
                    use_angle_cls=True
                )
    return _OCR_INSTANCE

class QuickOCR:
    def __init__(self):
        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("快捷OCR识字")
        self.root.attributes('-topmost', True)
        
        # 窗口大小和位置（屏幕中间偏右上）
        window_width = 200
        window_height = 100
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = screen_width //4*3- window_width // 2
        y = screen_height // 4 - window_height // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.attributes('-toolwindow', True)  # 去掉任务栏图标
        self.root.resizable(False, False)
        self.root.configure(bg='#3ee0f5')
        
        # 截图相关变量
        self.screenshot_mode = False
        self.screenshot_window = None
        self.screenshot_canvas = None
        self.rect = None
        self.start_x = self.start_y = self.end_x = self.end_y = 0
                
        # 程序运行标志
        self.running = True
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # 创建UI
        self.setup_ui()
        
        # 绑定全局快捷键
        self.setup_hotkeys()
        
        # 窗口拖动
        self.root.bind('<Button-1>', self.start_drag)
        self.root.bind('<B1-Motion>', self.on_drag)
        
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
        # OCR引擎（延迟初始化）
        # self.root.after(100, self.preload_ocr)
        _ = get_ocr_instance()
    # def preload_ocr(self):
    #     self.ocr_engine = RapidOCR(model_path='models/ocrmath.onnx')
    #     # self.update_status("OCR引擎加载中...")
    #     _ = get_ocr_instance()
    #     # self.update_status("OCR引擎加载完成")

    def setup_ui(self):


        """设置界面"""
        main_frame = tk.Frame(self.root, bg='#3ee0f5')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 截图按钮
        self.screenshot_btn = tk.Button(
            main_frame,
            text="截图识字(F4)",
            font=("Microsoft YaHei", 11, "bold"),
            bg='#3498db',
            fg='white',
            relief=tk.FLAT,
            bd=0,
            padx=15,
            pady=8,
            cursor='hand2',
            command=self.start_screenshot,
            activebackground='#2980b9',
            activeforeground='white'
        )
        self.screenshot_btn.pack(expand=True, fill=tk.BOTH)
        
        # 状态标签 - 所有信息统一在这里显示
        self.status_label = tk.Label(
            main_frame,
            text="按F4或点击按钮截图",
            font=("Microsoft YaHei", 8),
            bg='#3ee0f5',
            fg="#281b46",
            wraplength=200,
            justify=tk.CENTER
        )
        self.status_label.pack(expand=True, fill=tk.BOTH)
    
    def setup_hotkeys(self):
        """设置全局快捷键"""
        try:
            keyboard.add_hotkey('f4', self.start_screenshot)
            keyboard.add_hotkey('ctrl+shift+s', self.start_screenshot)
        except Exception as e:
            self.update_status("⚠️快捷键注册失败，请使用按钮")
    
    def start_drag(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def on_drag(self, event):
        x = self.root.winfo_x() + event.x - self.drag_start_x
        y = self.root.winfo_y() + event.y - self.drag_start_y
        self.root.geometry(f"+{x}+{y}")
    
    def start_screenshot(self):
        """开始截图模式"""
        if self.screenshot_mode or not self.running:
            return
        
        self.screenshot_mode = True
        self.update_status("截图模式: 框选区域 (ESC取消)")
        self.root.withdraw()
        self.root.after(100, self.create_screenshot_window)
    
    def create_screenshot_window(self):
        """创建截图窗口"""
        try:
            self.screenshot_window = tk.Toplevel(self.root)
            self.screenshot_window.attributes('-fullscreen', True)
            self.screenshot_window.attributes('-alpha', 0.3)
            self.screenshot_window.attributes('-topmost', True)
            self.screenshot_window.configure(bg='#3ee0f5')
            
            self.screenshot_canvas = tk.Canvas(
                self.screenshot_window,
                bg='black',
                highlightthickness=0,
                cursor='cross'
            )
            self.screenshot_canvas.pack(fill=tk.BOTH, expand=True)
            
            # 绑定鼠标事件
            self.screenshot_canvas.bind('<Button-1>', self.on_screenshot_press)
            self.screenshot_canvas.bind('<B1-Motion>', self.on_screenshot_drag)
            self.screenshot_canvas.bind('<ButtonRelease-1>', self.on_screenshot_release)
            
            # ESC取消
            self.screenshot_window.bind('<Escape>', self.cancel_screenshot)
            
            # 提示文字
            screen_width = self.screenshot_window.winfo_screenwidth()
            self.screenshot_canvas.create_text(
                screen_width // 2,
                50,
                text="按住鼠标左键拖动选择区域，ESC取消",
                fill='white',
                font=("Arial", 16, "bold")
            )
        except Exception:
            self.update_status("❌创建截图窗口失败")
            self.cancel_screenshot()
    
    def on_screenshot_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.screenshot_canvas.delete(self.rect)
        self.rect = self.screenshot_canvas.create_rectangle(
            self.start_x, self.start_y,
            self.start_x, self.start_y,
            outline="#2c73c3",
            width=3,
            fill='',
            dash=(5, 5)
        )
    
    def on_screenshot_drag(self, event):
        self.end_x = event.x
        self.end_y = event.y
        if self.rect:
            self.screenshot_canvas.coords(
                self.rect,
                self.start_x, self.start_y,
                self.end_x, self.end_y
            )
    
    def on_screenshot_release(self, event):
        self.end_x = event.x
        self.end_y = event.y
        
        x1 = min(self.start_x, self.end_x)
        y1 = min(self.start_y, self.end_y)
        x2 = max(self.start_x, self.end_x)
        y2 = max(self.start_y, self.end_y)
        
        if abs(x2 - x1) < 20 or abs(y2 - y1) < 20:
            self.update_status("⚠️选择区域太小，已取消")
            self.cancel_screenshot()
            return
        
        self.capture_and_process(x1, y1, x2, y2)
    
    def capture_and_process(self, x1, y1, x2, y2):
        """捕获截图并识别"""
        try:
            if self.screenshot_window:
                self.screenshot_window.destroy()
                self.screenshot_window = None
            
            self.update_status("正在截图...")
            screenshot = pyautogui.screenshot(region=(x1, y1, x2 - x1, y2 - y1))
            
            # 在新线程中识别
            threading.Thread(
                target=self.recognize_and_copy,
                args=(screenshot,),
                daemon=True
            ).start()
        except Exception as e:
            self.show_error(f"截图失败: {str(e)}")
            self.cancel_screenshot()
    
    def recognize_and_copy(self, image):
        """RapidOCR识别并复制到剪贴板"""
        try:
            self.root.after(0, lambda: self.update_status("⏳正在识别文字..."))

            # 获取全局ocr实例
            ocr = get_ocr_instance()
            
            # RapidOCR识别
            result, elapse = ocr(image)
            
            if not result:
                self.root.after(0, lambda: self.update_status("❌未识别到文字"))
                return

            # 按Y坐标排序
            sorted_boxes = sorted(result, key=lambda x: x[0][0][1])

            # 按Y坐标分组（同一行）
            lines = []
            current_line = []
            current_y = None
            y_threshold = 15  # Y坐标差15像素以内算同一行

            for line in sorted_boxes:
                if len(line) >= 3:
                    text = line[1]
                    confidence = line[2]
                    y_pos = line[0][0][1]
                    x_pos = line[0][0][0]

                    if confidence > 0.3:
                        if current_y is None or abs(y_pos - current_y) <= y_threshold:
                            # 同一行：添加文字
                            current_line.append((x_pos, text))
                        else:
                            # 新的一行：合并当前行，开始新行
                            if current_line:
                                current_line.sort(key=lambda x: x[0])  # 按X坐标排序
                                lines.append(' '.join([t[1] for t in current_line]))  # 空格连接
                            current_line = [(x_pos, text)]
                        current_y = y_pos

            # 处理最后一行
            if current_line:
                current_line.sort(key=lambda x: x[0])  # 按X坐标排序
                lines.append(' '.join([t[1] for t in current_line]))

            if lines:
                # 不同行之间用换行连接
                full_text = '\n'.join(lines)
                self.root.after(0, lambda: self.copy_to_clipboard(full_text, len(lines)))
            else:
                self.root.after(0, lambda: self.update_status("❌未识别到文字"))

        except Exception as e:
            error_msg = f"识别失败: {str(e)[:50]}..."
            self.root.after(0, lambda: self.show_error(error_msg))
        finally:
            self.screenshot_mode = False
            self.root.after(0, self.root.deiconify)
            self.root.after(0, lambda: self.root.lift())
    
    def copy_to_clipboard(self, text, count):
        """复制到系统剪贴板"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            
            # 显示成功信息（带预览）
            preview = text[:20] + "..." if len(text) > 20 else text
            preview = preview.replace('\n', ' ')  # 换行符显示为空格
            self.update_status(f"✅已复制{count}段:Ctrl+V粘贴")
        except Exception as e:
            self.show_error(f"复制失败: {str(e)}")
    
    def cancel_screenshot(self, event=None):
        """取消截图"""
        if self.screenshot_window:
            try:
                self.screenshot_window.destroy()
            except:
                pass
            self.screenshot_window = None
        self.screenshot_mode = False
        self.root.deiconify()
        self.root.lift()
        self.update_status("已取消")
    
    def show_error(self, message):
        """错误提示 - 同时显示在状态栏和弹窗"""
        self.update_status(f"❌{message}")
        messagebox.showerror("错误", message, parent=self.root)
    
    def update_status(self, message):
        """统一状态更新 - 所有信息都在这里显示"""
        try:
            self.status_label.config(text=message)
            self.root.update_idletasks()
        except:
            pass
    
    def on_closing(self):
        """窗口关闭"""
        self.running = False
        try:
            keyboard.unhook_all_hotkeys()
        except:
            pass
        self.root.quit()
        self.root.destroy()
        sys.exit(0)
    
    def run(self):
        """运行程序"""
        self.update_status("按F4或点击按钮截图")
        self.root.mainloop()

def main():
    try:
        app = QuickOCR()
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        # 最后的错误处理 - 仅当窗口都无法创建时使用弹窗
        try:
            import tkinter.messagebox as mb
            mb.showerror("启动错误", f"程序启动失败:\n{str(e)}")
        except:
            pass
    finally:
        try:
            keyboard.unhook_all_hotkeys()
        except:
            pass
        sys.exit(0)


if __name__ == "__main__":
    main()