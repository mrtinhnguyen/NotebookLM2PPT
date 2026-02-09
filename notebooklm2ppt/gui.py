import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import sys
import os
import difflib
import windnd
from pathlib import Path
from .cli import process_pdf_to_ppt
from .utils.ppt_combiner import combine_ppt, create_ppt_from_images
from .utils.screenshot_automation import screen_width, screen_height
from .utils.ppt_refiner import refine_ppt
from .utils.image_inpainter import get_method_names, METHOD_ID_TO_NAME, get_method_name_from_id
from .pdf2png import pdf_to_png
import json
import ctypes
import webbrowser
from . import __version__
from .i18n import get_text, SUPPORTED_LANGUAGES, set_language
from .utils.process_checker import is_process_running, PROCESS_NAME
from .config_defaults import DEFAULT_TASK_SETTINGS, DEFAULT_AUTOMATION_SETTINGS, get_default_settings

MINERU_URL = "https://mineru.net/"
GITHUB_URL = "https://github.com/mrtinhnguyen/NotebookLM2PPT"
PC_MANAGER_URL = "https://pcmanager.microsoft.com/"


CONFIG_FILE = Path("./config.json")


BASE_WINDOWS_DPI = 85


def icon_path():
    """Lấy đường dẫn tài nguyên tuyệt đối, áp dụng cho PyInstaller sau khi đóng gói"""
    try:
        return os.path.join(sys._MEIPASS, "favicon.ico")
    except Exception:
        return os.path.abspath("./docs/public/favicon.ico")
    
def enable_windows_dpi_awareness(root=None):
    """Enable DPI awareness on Windows and adjust Tk scaling.

    Call this before creating UI or immediately after creating `root`.
    This helps fix display issues when Windows scaling is 200%.
    """
    if sys.platform != "win32":
        return
    # Try modern APIs first, fall back gracefully
    try:
        user32 = ctypes.windll.user32
        # Try SetProcessDpiAwarenessContext (Windows 10+)
        if hasattr(user32, 'SetProcessDpiAwarenessContext'):
            try:
                # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
                user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            except Exception:
                pass
        else:
            # Try shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE=2)
            try:
                shcore = ctypes.windll.shcore
                shcore.SetProcessDpiAwareness(2)
            except Exception:
                # Older fallback
                try:
                    user32.SetProcessDPIAware()
                except Exception:
                    pass

        # If a root was provided, try to set tk scaling to system DPI
        if root is not None:
            try:
                # Get system DPI (fallback to 96)
                dpi = BASE_WINDOWS_DPI
                
                if hasattr(user32, 'GetDpiForSystem'):
                    dpi = user32.GetDpiForSystem()
                elif hasattr(user32, 'GetDeviceCaps'):
                    # Last resort: get DC dpi
                    hdc = user32.GetDC(0)
                    # LOGPIXELSX = 88
                    gdi32 = ctypes.windll.gdi32
                    dpi = gdi32.GetDeviceCaps(hdc, 88)
                scaling = float(dpi) / BASE_WINDOWS_DPI
                print(f"Hệ thống DPI: {dpi}, hệ số cân: {scaling}")
                root.tk.call('tk', 'scaling', scaling)
            except Exception:
                pass
    except Exception:
        pass


class TextRedirector:
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        self.widget.configure(state='normal')
        self.widget.insert(tk.END, str, (self.tag,))
        self.widget.see(tk.END)
        self.widget.configure(state='disabled')

    def flush(self):
        pass

class AppGUI:
    def __init__(self, root):
        self.root = root
        self.lang = "vi"  # Default
        self.top_left = (10, 10)
        
        # Khởi tạo hàng đợi kéo thả và cơ chế bộ đếm (để xử lý an toàn luồng)
        self._drop_queue = queue.Queue()
        self._poll_drop_queue()
        
        self.load_config_from_disk()
        set_language(self.lang)
        
        self.root.title(get_text("root_title", version=__version__))
        self.root.geometry("850x920")
        self.root.minsize(750, 850)
        self.center_window()
        
        self.stop_flag = False
        
        self.show_startup_dialog()
        
        self.setup_ui()
        
        # Load config again to populate UI variables
        self.load_config_from_disk()
        
        # Save original stdout/stderr
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        
        # Redirect stdout and stderr
        sys.stdout = TextRedirector(self.log_area, "stdout")
        sys.stderr = TextRedirector(self.log_area, "stderr")
        
        # Giao diện chính không còn hỗ trợ chức năng kéo thả
        # if windnd:
        #     windnd.hook_dropfiles(self.root, func=self.on_drop_files)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _poll_drop_queue(self):
        """Quản lý hàng đợi kéo thả, xử lý sự kiện kéo thả trong luồng chính"""
        try:
            while True:
                try:
                    item = self._drop_queue.get_nowait()
                    drop_type = item[0]
                    
                    if drop_type == 'pdf':
                        _, files, pdf_listbox, pairing_dict, sync_func, update_func = item
                        self._handle_batch_pdf_drop(files, pdf_listbox, pairing_dict, sync_func, update_func)
                    elif drop_type == 'json':
                        _, files, json_listbox, pairing_dict, sync_func, update_func = item
                        self._handle_batch_json_drop(files, json_listbox, pairing_dict, sync_func, update_func)
                    elif drop_type == 'dialog':
                        _, files, pdf_var, json_var = item
                        self._handle_dialog_drop_files_impl(files, pdf_var, json_var)
                        
                except queue.Empty:
                    break
        except Exception as e:
            print(f"Lỗi khi xử lý hàng đợi kéo thả: {e}")
        finally:
            # Kiểm tra mỗi 100ms
            self.root.after(100, self._poll_drop_queue)

    def _setup_path_entry(self, entry):
        """Thêm menu bối cảnh, chọn toàn bộ và chức năng cuộn tự động cho ô nhập đường dẫn"""
        self.add_context_menu(entry)
        entry.bind("<FocusIn>", lambda e: entry.selection_range(0, tk.END))
        entry.bind("<FocusOut>", lambda e: entry.xview_moveto(1.0))
        # Hiển thị đầu tiên (tên tệp)
        self.root.after(200, lambda: entry.xview_moveto(1.0))

    def set_var_and_scroll(self, var, entry, value):
        """Cài đặt giá trị biến và cuộn Entry đến cuối để hiển thị tên tệp"""
        var.set(value)
        # Sử dụng after để đảm bảo cuộn sau khi Tkinter cập nhật
        self.root.after(10, lambda: entry.xview_moveto(1.0))

    def _get_display_path(self, path):
        """Lấy đường dẫn để hiển thị Treeview (chỉ hiển thị tên tệp)"""
        if not path:
            return ""
        return os.path.basename(path)

    # Giao diện chính không còn hỗ trợ chức năng kéo thả, đã chuyển sang tính năng ghép cặp hàng loạt
    # def on_drop_files(self, files):
    #     if files:
    #         decoded_files = []
    #         for f in files:
    #             decoded_files.append(f.decode('gbk') if isinstance(f, bytes) else f)
    #         pdfs = [f for f in decoded_files if f.lower().endswith('.pdf')]
    #         jsons = [f for f in decoded_files if f.lower().endswith('.json')]
    #         if len(pdfs) <= 1 and len(decoded_files) == 1:
    #             file_path = decoded_files[0]
    #             lower_file_path = file_path.lower()
    #             if lower_file_path.endswith('.pdf'):
    #                 self.set_var_and_scroll(self.pdf_path_var, self.pdf_entry, file_path)
    #                 print(get_text("file_added_msg", file=file_path))
    #             elif lower_file_path.endswith('.json'):
    #                 self.set_var_and_scroll(self.mineru_json_var, self.mineru_entry, file_path)
    #             else:
    #                 messagebox.showwarning(get_text("info_btn"), get_text("drag_drop_warning"))
    #             return
    #         if pdfs:
    #             json_map = {Path(j).stem: j for j in jsons}
    #             for p in pdfs:
    #                 matched_json = json_map.get(Path(p).stem, "")
    #                 if not matched_json and len(jsons) == 1:
    #                     matched_json = jsons[0]
    #                 self.add_task(p, matched_json or None)
    #         else:
    #             messagebox.showwarning(get_text("info_btn"), get_text("drag_drop_warning"))

    def on_closing(self):
        self.dump_config_to_disk()
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        self.root.destroy()

    def center_window(self):
        """Căn giữa cửa sổ để hiển thị"""
        width = 850
        height = 920
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def create_toplevel(self, title, width, height):
        """Tạo cửa sổ Toplevel với cài đặt biểu tượng"""
        top = tk.Toplevel(self.root)
        top.title(title)
        # Cố gắng thiết lập biểu tượng một cách an toàn (bỏ qua nếu không hỗ trợ)
        try:
            ico = icon_path()
            if ico and os.path.exists(ico):
                try:
                    top.iconbitmap(ico)
                except Exception:
                    try:
                        top.iconbitmap(default=ico)
                    except Exception:
                        pass
        except Exception:
            pass
        self.center_toplevel(top, width, height)
        # Đặt thuộc tính cửa sổ (không sử dụng chế độ modal để tránh xung đột với chức năng kéo thả)
        top.transient(self.root)
        return top

    def center_toplevel(self, window, width, height):
        """Căn giữa cửa sổ Toplevel để hiển thị"""
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'{width}x{height}+{x}+{y}')

    def change_language(self, new_lang):
        """Chuyển đổi ngôn ngữ và khởi động lại giao diện người dùng"""
        if self.lang == new_lang:
            return
        
        self.lang = new_lang
        set_language(self.lang)
        self.dump_config_to_disk()
        
        # Cập nhật tiêu đề cửa sổ tập thể
        self.root.title(get_text("root_title", version=__version__))
        
        # QuẪ lý lại giao diện thlavní
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame) or isinstance(widget, tk.Frame):
                widget.destroy()
        
        self.setup_ui()
        # Hướng dẫn lại stdout/stderr đến log_area mới
        sys.stdout = TextRedirector(self.log_area, "stdout")
        sys.stderr = TextRedirector(self.log_area, "stderr")

    def add_context_menu(self, widget):
        """Thêm menu bối cảnh cho ô nhập (cắt, sao chép, dán, chọn tất cả)"""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label=get_text("cut"), command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label=get_text("copy"), command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label=get_text("paste"), command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label=get_text("select_all"), command=lambda: widget.select_range(0, tk.END))
        
        def show_menu(event):
            menu.post(event.x_root, event.y_root)
        
        widget.bind("<Button-3>", show_menu)

    def get_translated_method_names(self):
        """Lấy danh sách tên phương thức đã dịch"""
        from .utils.image_inpainter import INPAINT_METHODS
        return [get_text(f"method_{m['id']}_name") for m in INPAINT_METHODS]

    def get_method_id_from_translated_name(self, translated_name):
        """Lấy ID từ tên phương thức đã dịch"""
        from .utils.image_inpainter import INPAINT_METHODS
        for m in INPAINT_METHODS:
            if get_text(f"method_{m['id']}_name") == translated_name:
                return m['id']
        return "background_smooth"

    def get_translated_name_from_id(self, method_id):
        """Lấy tên đã dịch từ ID"""
        return get_text(f"method_{method_id}_name")

    def on_language_combo_change(self, event):
        """Xử lý thay đổi lựa chọn hộp chọn ngôn ngữ"""
        selected_name = self.lang_combo_var.get()
        for code in SUPPORTED_LANGUAGES.keys():
            if get_text(f"lang_{code}") == selected_name:
                self.change_language(code)
                return

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)

        self.task_queue = getattr(self, 'task_queue', [])
        self.task_id_counter = getattr(self, 'task_id_counter', 1)
        self.queue_thread = None
        self.queue_stop_flag = False
        self.is_queue_running = False

        # Global Settings (Cài đặt toàn cục)
        global_frame = ttk.LabelFrame(main_frame, text=get_text("global_settings_label"), padding="10")
        global_frame.pack(fill=tk.X, pady=5)
        global_frame.columnconfigure(1, weight=1)

        # Lựa chọn ngôn ngữ (trên dòng đầu tiên ở cài đặt toàn cục)
        ttk.Label(global_frame, text=get_text("ui_language_label")).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        lang_display_names = [get_text(f"lang_{code}") for code in SUPPORTED_LANGUAGES.keys()]
        current_lang_display = get_text(f"lang_{self.lang}")
        
        self.lang_combo_var = tk.StringVar(value=current_lang_display)
        lang_combo = ttk.Combobox(global_frame, textvariable=self.lang_combo_var, values=lang_display_names, state="readonly", width=15)
        lang_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        lang_combo.bind("<<ComboboxSelected>>", self.on_language_combo_change)

        # Thư mục đầu ra (mặc định toàn cục)
        ttk.Label(global_frame, text=get_text("output_dir_label")).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_dir_var = getattr(self, 'output_dir_var', tk.StringVar(value="workspace"))
        self.output_entry = ttk.Entry(global_frame, textvariable=self.output_dir_var, width=60)
        self.output_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self._setup_path_entry(self.output_entry)
        ttk.Button(global_frame, text=get_text("browse_btn"), command=self.browse_output).grid(row=1, column=2, pady=5)
        ttk.Button(global_frame, text=get_text("open_btn"), command=self.open_output_dir).grid(row=1, column=3, pady=5, padx=5)

        # Automation Settings (Cài đặt tự động hóa liên quan)
        opt_frame = ttk.LabelFrame(main_frame, text=get_text("automation_settings_label"), padding="10")
        opt_frame.pack(fill=tk.X, pady=5)
        opt_frame.columnconfigure(1, weight=1)
        opt_frame.columnconfigure(3, weight=1)

        # Dòng 1: Thời gian chờ và Thời gian quá
        ttk.Label(opt_frame, text=get_text("delay_label")).grid(row=0, column=0, sticky=tk.W)
        self.delay_var = getattr(self, 'delay_var', tk.IntVar(value=0))
        delay_entry = ttk.Entry(opt_frame, textvariable=self.delay_var, width=8)
        delay_entry.grid(row=0, column=1, sticky=tk.W, padx=5)
        self.add_context_menu(delay_entry)
        ttk.Label(opt_frame, text=get_text("delay_hint"), foreground="gray").grid(row=0, column=2, sticky=tk.W, padx=5)

        ttk.Label(opt_frame, text=get_text("timeout_label")).grid(row=0, column=3, sticky=tk.W, padx=(20, 0))
        self.timeout_var = getattr(self, 'timeout_var', tk.IntVar(value=50))
        timeout_entry = ttk.Entry(opt_frame, textvariable=self.timeout_var, width=8)
        timeout_entry.grid(row=0, column=4, sticky=tk.W, padx=5)
        self.add_context_menu(timeout_entry)
        ttk.Label(opt_frame, text=get_text("timeout_hint"), foreground="gray").grid(row=0, column=5, sticky=tk.W, padx=5)

        # Dòng 2: Độ lệch núp và Tự động hiệu chuẩn
        ttk.Label(opt_frame, text=get_text("button_offset_label")).grid(row=5, column=0, sticky=tk.W, pady=5)
        self.done_offset_var = getattr(self, 'done_offset_var', tk.StringVar(value=""))
        done_offset_entry = ttk.Entry(opt_frame, textvariable=self.done_offset_var, width=8)
        done_offset_entry.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        self.add_context_menu(done_offset_entry)
        self.saved_offset_var = getattr(self, 'saved_offset_var', tk.StringVar(value=""))
        ttk.Label(opt_frame, textvariable=self.saved_offset_var, foreground="blue").grid(row=5, column=2, sticky=tk.W, padx=5, pady=5)

        self.calibrate_var = getattr(self, 'calibrate_var', tk.BooleanVar(value=True))
        ttk.Checkbutton(opt_frame, text=get_text("calibrate_label"), variable=self.calibrate_var).grid(row=5, column=3, columnspan=3, sticky=tk.W, pady=5, padx=(20, 0))

        # Thông báo gợi ý
        ttk.Label(opt_frame, text=get_text("core_param_warning"), foreground="red").grid(row=6, column=0, columnspan=6, sticky=tk.W)
        ttk.Label(opt_frame, text=get_text("core_param_warning2"), foreground="red").grid(row=7, column=0, columnspan=6, sticky=tk.W)
        ttk.Label(opt_frame, text=get_text("core_param_warning3"), foreground="red").grid(row=8, column=0, columnspan=6, sticky=tk.W)


        # Queue Control
        queue_frame = ttk.LabelFrame(main_frame, text=get_text("queue_label"), padding="10")
        queue_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        queue_frame.columnconfigure(0, weight=1)
        queue_frame.rowconfigure(0, weight=1)

        columns = ("id", "pdf", "json", "status", "output")
        self.queue_tree = ttk.Treeview(queue_frame, columns=columns, show="headings", height=5)
        self.queue_tree.heading("id", text=get_text("queue_col_id"))
        self.queue_tree.heading("pdf", text=get_text("queue_col_pdf"))
        self.queue_tree.heading("json", text=get_text("queue_col_json"))
        self.queue_tree.heading("status", text=get_text("queue_col_status"))
        self.queue_tree.heading("output", text=get_text("queue_col_output"))
        self.queue_tree.column("id", width=60, anchor="center", stretch=False)
        self.queue_tree.column("pdf", width=200, stretch=True)
        self.queue_tree.column("json", width=150, stretch=True)
        self.queue_tree.column("status", width=100, anchor="center", stretch=False)
        self.queue_tree.column("output", width=200, stretch=True)
        self.queue_tree.grid(row=0, column=0, columnspan=6, sticky="nsew", pady=(0, 8))
        self.queue_tree.bind("<Double-1>", self.on_task_double_click)

        for task in self.task_queue:
            self.queue_tree.insert("", tk.END, iid=str(task["id"]), values=(
                task["id"], 
                self._get_display_path(task["pdf"]), 
                self._get_display_path(task["json"]), 
                task["status"], 
                self._get_display_path(task["output"])
            ))

        queue_btns = ttk.Frame(queue_frame)
        queue_btns.grid(row=1, column=0, columnspan=6, sticky="ew")
        
        self.start_btn = ttk.Button(queue_btns, text=get_text("start_btn"), command=self.start_queue)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(queue_btns, text=get_text("stop_btn"), command=self.stop_queue, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(queue_btns, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        ttk.Button(queue_btns, text=get_text("queue_add_task"), command=self.add_task_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(queue_btns, text=get_text("queue_add_multi_pdf"), command=self.add_tasks_batch_pair).pack(side=tk.LEFT, padx=5)
        ttk.Button(queue_btns, text=get_text("queue_remove_selected"), command=self.remove_selected_task).pack(side=tk.LEFT, padx=5)
        ttk.Button(queue_btns, text=get_text("queue_clear"), command=self.clear_tasks).pack(side=tk.LEFT, padx=5)

        # Log Area
        log_frame = ttk.LabelFrame(main_frame, text=get_text("log_area_label"), padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_area = scrolledtext.ScrolledText(log_frame, state='disabled', height=12)
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.log_area.tag_config("stderr", foreground="red")



    def browse_output(self):
        # Xóa dấu ngoặc và khoảng trắng trong đường dẫn
        current_dir = self.output_dir_var.get().strip().strip('"')
        initial_dir = current_dir if current_dir and os.path.exists(current_dir) else None
        
        directory = filedialog.askdirectory(
            parent=self.root,
            title=get_text("select_output_title"),
            initialdir=initial_dir
        )
        if directory:
            self.set_var_and_scroll(self.output_dir_var, self.output_entry, directory)
            print(get_text("set_new_dir_msg", directory=directory))

    def open_output_dir(self):
        output_dir = self.output_dir_var.get().strip().strip('"')
        if not output_dir:
            messagebox.showwarning(get_text("info_btn"), get_text("set_output_dir_warning"))
            return
        
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                print(get_text("create_output_dir_msg", output_dir=output_dir))
            except Exception as e:
                messagebox.showerror(get_text("error_btn"), get_text("create_output_dir_error", error=str(e)))
                return
        
        try:
            os.startfile(output_dir)
        except Exception as e:
            messagebox.showerror(get_text("error_btn"), get_text("open_output_dir_error", error=str(e)))





    def show_inpaint_method_info(self):
        from .utils.image_inpainter import INPAINT_METHODS
        
        info_lines = [get_text("inpaint_method_info_prefix")]
        for method in INPAINT_METHODS:
            name = get_text(f"method_{method['id']}_name")
            desc = get_text(f"method_{method['id']}_desc")
            info_lines.append(f"• {name}\n  {desc}\n")
        
        info = "".join(info_lines)
        
        top = self.create_toplevel(get_text("inpaint_method_info_title"), 600, 400)
        txt = scrolledtext.ScrolledText(top, wrap=tk.WORD, height=15)
        txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8,6))
        txt.insert(tk.END, info)
        txt.configure(state='disabled')
        btn_frame = ttk.Frame(top)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=6)
        ttk.Button(btn_frame, text=get_text("close_btn"), command=top.destroy).pack(side=tk.LEFT, padx=6)

    def ensure_pc_manager_running(self):
        if sys.platform != "win32":
            return True
        try:
            running = is_process_running(PROCESS_NAME)
        except Exception as e:
            messagebox.showerror(
                get_text("error_btn"),
                f"Không thể kiểm tra trạng thái Quản lý máy tính: {e}",
            )
            return False
        if not running:
            full_msg = (
                get_text("pc_manager_not_running_msg")
                + "\n\n"
                + get_text("pc_manager_open_website_confirm")
            )
            open_site = messagebox.askyesno(
                get_text("error_btn"),
                full_msg,
            )
            if open_site:
                try:
                    webbrowser.open_new_tab(PC_MANAGER_URL)
                except Exception as e:
                    messagebox.showerror(
                        get_text("error_btn"),
                        get_text("open_pc_manager_website_error", error=str(e)),
                    )
            return False
        return True



    def dump_config_to_disk(self):
        # Trước tiên đọc cấu hình hiện có, giữ lại các trường khác như hide_startup_dialog
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            else:
                config_data = {}
        except Exception:
            config_data = {}
        
        # Cập nhật các trường cần lưu
        config_data.update({
            "language": self.lang,
            "output_dir": self.output_dir_var.get(),
            "delay": self.delay_var.get(),
            "timeout": self.timeout_var.get(),
            "done_offset": self.done_offset_var.get(),
            # Lưu cài đặt tác vụ mà người dùng sử dụng lần trước (chỉ lưu các giá trị mà người dùng có thể sửa đổi)
            "last_task_settings": getattr(self, 'last_task_settings', {})
        })
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            print(get_text("config_saved"))
        except Exception as e:
            print(get_text("config_save_fail", error=str(e)))

    def load_config_from_disk(self):
        try:
            if not CONFIG_FILE.exists():
                self.last_task_settings = {}  # Khởi tạo thành từ điển trống
                return
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                self.lang = config_data.get("language", "vi")
                # Tải cài đặt tác vụ mà người dùng sử dụng lần trước
                self.last_task_settings = config_data.get("last_task_settings", {})
                if hasattr(self, 'output_dir_var'):
                    self.output_dir_var.set(config_data.get("output_dir", "workspace"))
                    self.delay_var.set(config_data.get("delay", 0))
                    self.timeout_var.set(config_data.get("timeout", 50))
                    offset_value = config_data.get("done_offset", "")
                    self.update_offset_related_gui(offset_value)
                    
                    # Đảm bảo cuộn đến cuối sau khi tải cấu hình để hiển thị tên tệp
                    if hasattr(self, 'output_entry'):
                        self.root.after(100, lambda: self.output_entry.xview_moveto(1.0))
        except Exception as e:
            print(get_text("config_load_fail", error=str(e)))
            self.dump_config_to_disk()
            print(get_text("default_config_created"))


    def update_offset_disk(self, offset_value):
        self.done_offset_var.set(str(offset_value))
        self.dump_config_to_disk()
        self.update_offset_related_gui(offset_value)

    def update_offset_related_gui(self, done_offset_value=None):
        saved = done_offset_value
        is_valid = saved is not None and saved != ""
        if is_valid:
            self.saved_offset_var.set(get_text("saved_offset", offset=saved))
            if not self.done_offset_var.get().strip():
                self.done_offset_var.set(str(saved))
        else:
            self.saved_offset_var.set(get_text("unsaved_offset"))
        self.calibrate_var.set(not is_valid)
        
    def show_startup_dialog(self):
        config_file = Path("./config.json")
        show_dialog = True
        
        try:
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    show_dialog = not config_data.get("hide_startup_dialog", False)
        except Exception:
            pass
        
        if not show_dialog:
            return
        
        top = self.create_toplevel(get_text("startup_dialog_title"), 500, 300)
        top.resizable(False, False)
        
        info_frame = ttk.Frame(top, padding="20")
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        info_text = get_text("startup_info")
        
        txt = scrolledtext.ScrolledText(info_frame, wrap=tk.WORD, height=8)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert(tk.END, info_text)
        txt.configure(state='disabled')
        
        btn_frame = ttk.Frame(info_frame)
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        
        def open_github():
            try:
                webbrowser.open_new_tab(GITHUB_URL)
            except Exception as e:
                messagebox.showerror(get_text("error_btn"), f"Không thể mở trang web: {e}")
        
        def on_ok():
            top.destroy()
        
        def on_dont_show():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            except Exception:
                config_data = {}
            
            config_data["hide_startup_dialog"] = True
            
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=4)
            except Exception as e:
                print(get_text("config_save_fail", error=str(e)))
            
            top.destroy()
        
        ttk.Button(btn_frame, text=get_text("open_github_btn"), command=open_github).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=get_text("dont_show_again_btn"), command=on_dont_show).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text=get_text("ok_btn"), command=on_ok).pack(side=tk.RIGHT, padx=5)
        
        top.transient(self.root)
        # Sử dụng cửa sổ không đồng bộ (không sử dụng modal), tránh chặn và xung đột kéo thả
        
    def show_mineru_info(self):
        info = get_text("mineru_info_content")
        top = self.create_toplevel(get_text("mineru_info_title"), 640, 360)
        txt = scrolledtext.ScrolledText(top, wrap=tk.WORD, height=12)
        txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8,6))
        txt.insert(tk.END, info)
        txt.configure(state='disabled')
        btn_frame = ttk.Frame(top)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=6)

        def open_mineru_website():
            try:
                webbrowser.open_new_tab(MINERU_URL)
            except Exception as e:
                messagebox.showerror(get_text("error_btn"), f"Không thể mở trang web: {e}")

        ttk.Button(btn_frame, text=get_text("open_mineru_website"), command=open_mineru_website).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text=get_text("close_btn"), command=top.destroy).pack(side=tk.LEFT, padx=6)
        
    def run_conversion(self):
        try:
            pdf_file = self.pdf_path_var.get()
            pdf_name = Path(pdf_file).stem
            workspace_dir = Path(self.output_dir_var.get())
            png_dir = workspace_dir / f"{pdf_name}_pngs"
            ppt_dir = workspace_dir / f"{pdf_name}_ppt"
            tmp_image_dir = workspace_dir / "tmp_images"
            
            workspace_dir.mkdir(exist_ok=True, parents=True)

            offset_raw = self.done_offset_var.get().strip()
            done_offset = None
            if offset_raw:
                try:
                    done_offset = int(offset_raw)
                except ValueError:
                    raise ValueError(get_text("offset_value_error"))

            ratio = min(screen_width/16, screen_height/9)
            max_display_width = int(16 * ratio)
            max_display_height = int(9 * ratio)

            display_width = int(max_display_width * self.ratio_var.get())
            display_height = int(max_display_height * self.ratio_var.get())

            print(get_text("start_processing", file=pdf_file))

            # Phân tích phạm vi trang
            def parse_page_range(range_str):
                if not range_str:
                    return None
                pages = set()
                # Thay thế dấu phẩy tiếng Trung bằng dấu phẩy tiếng Anh
                range_str = range_str.replace('，', ',')
                # Thay thế các loại dấu gạch ngang tiếng Trung bằng dấu gạch ngang tiếng Anh
                range_str = range_str.replace('—', '-').replace('–', '-').replace('－', '-')
                for part in [p.strip() for p in range_str.split(',') if p.strip()]:
                    if '-' in part:
                        start_end = part.split('-')
                        if start_end[0] == '':
                            continue
                        start = int(start_end[0])
                        if start_end[1] == '':
                            pages.update(range(start, start + 10000))
                        else:
                            end = int(start_end[1])
                            if end >= start:
                                pages.update(range(start, end + 1))
                    else:
                        pages.add(int(part))
                return sorted(pages)

            # Chuyển đổi danh sách s ố trang thành định dạng chuỗi
            def format_page_suffix(pages):
                if not pages:
                    return ""
                result = []
                i = 0
                while i < len(pages):
                    start = pages[i]
                    end = start
                    while i + 1 < len(pages) and pages[i + 1] == end + 1:
                        i += 1
                        end = pages[i]
                    if start == end:
                        result.append(str(start))
                    else:
                        result.append(f"{start}-{end}")
                    i += 1
                return f"_p{','.join(result)}"

            pages_list = None
            try:
                pages_list = parse_page_range(self.page_range_var.get().strip())
            except Exception as e:
                raise ValueError(get_text("page_range_error"))
            
            # Tạo hậu tố tên tệp dựa trên phạm vi số trang
            page_suffix = format_page_suffix(pages_list)
            out_ppt_file = workspace_dir / f"{pdf_name}{page_suffix}.pptx"
            
            method_id = self.get_method_id_from_translated_name(self.inpaint_method_var.get())

            
            if self.image_only_var.get():
                print("=" * 60)
                print(get_text("image_only_mode_start"))
                print("=" * 60)
                
                png_names = pdf_to_png(
                    pdf_path=pdf_file,
                    output_dir=png_dir,
                    dpi=self.dpi_var.get(),
                    inpaint=self.inpaint_var.get(),
                    pages=pages_list,
                    inpaint_method=method_id,
                    force_regenerate=self.force_regenerate_var.get()
                )
                
                if self.stop_flag:
                    print("\n" + get_text("conversion_stopped_msg"))
                    messagebox.showinfo(get_text("conversion_stopped_title"), get_text("conversion_stopped_msg"))
                    return
                
                png_names = create_ppt_from_images(png_dir, out_ppt_file, png_names=png_names)
                extra_message = f" ({get_text('image_only_label')})"
            else:
                png_names = process_pdf_to_ppt(
                    pdf_path=pdf_file,
                    png_dir=png_dir,
                    ppt_dir=ppt_dir,
                    delay_between_images=self.delay_var.get(),
                    inpaint=self.inpaint_var.get(),
                    dpi=self.dpi_var.get(),
                    timeout=self.timeout_var.get(),
                    display_height=display_height,
                    display_width=display_width,
                    done_button_offset=done_offset,
                    capture_done_offset=self.calibrate_var.get(),
                    pages=pages_list,
                    update_offset_callback=self.update_offset_disk,
                    stop_flag=lambda: self.stop_flag,
                    force_regenerate=self.force_regenerate_var.get(),
                    inpaint_method=method_id,
                    top_left=self.top_left
                )

                if self.stop_flag:
                    print("\n" + get_text("conversion_stopped_msg"))
                    messagebox.showinfo(get_text("conversion_stopped_title"), get_text("conversion_stopped_msg"))
                    return

                png_names = combine_ppt(ppt_dir, out_ppt_file, png_names=png_names)
                extra_message = ""
            if not self.image_only_var.get():
                # Nếu người dùng cung cấp JSON MinerU, hãy thực hiện xử lý refine_ppt
                mineru_json = self.mineru_json_var.get().strip().strip('"')
                if mineru_json:
                    if not os.path.exists(mineru_json):
                        print(f"⚠️ {mineru_json} not exists")
                    else:
                        refined_out = workspace_dir / f"{pdf_name}{page_suffix}_optimized.pptx"
                        print(get_text("mineru_optimizing", file=mineru_json))
                        refine_ppt(str(tmp_image_dir), mineru_json, str(out_ppt_file), str(png_dir), png_names, str(refined_out), unify_font=unify_font, font_name=font_name)
                        
                        print(get_text("refine_ppt_done"))
                        extra_message = "\n\n" + get_text("refine_extra_msg")
                        out_ppt_file = os.path.abspath(refined_out)
                else:
                    extra_message = ""
            else:
                extra_message = f" ({get_text('image_only_label')})"
            out_ppt_file = os.path.abspath(out_ppt_file)
            print("\n" + get_text("conversion_done"))
            print(get_text("output_file", file=out_ppt_file))
            os.startfile(out_ppt_file)
            messagebox.showinfo(get_text("conversion_success_title"), get_text("conversion_success_msg", file=out_ppt_file) + extra_message)
        except Exception as e:
            print("\n" + get_text("conversion_fail", error=str(e)))
            messagebox.showerror(get_text("conversion_fail_title"), get_text("conversion_fail_msg", error=str(e)))
        finally:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    def add_task_with_settings(self, pdf_path, json_path=None, settings=None):
        """Thêm tác vụ bằng cách sử dụng các cài đặt được chỉ định"""
        if settings is None:
            # Nếu không cung cấp cài đặt, hãy sử dụng cài đặt lần trước của người dùng (nếu có)
            settings = get_default_settings(
                output_dir=self.output_dir_var.get().strip().strip('"'),
                inpaint_method=self.get_translated_method_names()[0],
                user_last_settings=getattr(self, 'last_task_settings', {})
            )
        else:
            # Lưu cài đặt mà người dùng sử dụng lần này (loại trừ các tham số động)
            self.last_task_settings = {k: v for k, v in settings.items() 
                                       if k not in ['output_dir', 'page_range']}
            self.dump_config_to_disk()  # Lưu ngay lập tức vào tệp cấu hình

        # Kiểm tra xem đã có tác vụ cho cùng một PDF không
        for task in self.task_queue:
            if task["pdf"] == pdf_path:
                # Cập nhật đường dẫn JSON của tác vụ hiện có, trạng thái và tất cả các cài đặt
                task["json"] = json_path or ""
                task["status"] = get_text("queue_status_pending")
                task["settings"] = settings
                self.update_task_row(task)
                print(get_text("queue_task_updated", file=pdf_path))
                return

        task = {
            "id": self.task_id_counter,
            "pdf": pdf_path,
            "json": json_path or "",
            "status": get_text("queue_status_pending"),
            "output": "",
            "settings": settings
        }
        self.task_queue.append(task)
        self.queue_tree.insert("", tk.END, iid=str(task["id"]), values=(
            task["id"], 
            self._get_display_path(task["pdf"]), 
            self._get_display_path(task["json"]), 
            task["status"], 
            self._get_display_path(task["output"])
        ))
        self.task_id_counter += 1
        print(get_text("queue_task_added", file=pdf_path))

    def add_task(self, pdf_path, json_path=None):
        """Thêm tác vụ (sử dụng cài đặt mặc định)"""
        settings = get_default_settings(
            output_dir=self.output_dir_var.get().strip().strip('"'),
            inpaint_method=self.get_translated_method_names()[0],
            user_last_settings=getattr(self, 'last_task_settings', {})
        )

        # Kiểm tra xem đã có tác vụ cho cùng một PDF không
        for task in self.task_queue:
            if task["pdf"] == pdf_path:
                # Cập nhật đường dẫn JSON của tác vụ hiện có, trạng thái và tất cả các cài đặt
                task["json"] = json_path or ""
                task["status"] = get_text("queue_status_pending")
                task["settings"] = settings
                self.update_task_row(task)
                print(get_text("queue_task_updated", file=pdf_path))
                return

        task = {
            "id": self.task_id_counter,
            "pdf": pdf_path,
            "json": json_path or "",
            "status": get_text("queue_status_pending"),
            "output": "",
            "settings": settings
        }
        self.task_queue.append(task)
        self.queue_tree.insert("", tk.END, iid=str(task["id"]), values=(
            task["id"], 
            self._get_display_path(task["pdf"]), 
            self._get_display_path(task["json"]), 
            task["status"], 
            self._get_display_path(task["output"])
        ))
        self.task_id_counter += 1
        print(get_text("queue_task_added", file=pdf_path))

    def add_task_dialog(self):
        """Hiển thị hộp thoại để cấu hình tất cả các tham số cho tác vụ mới"""
        top = self.create_toplevel(get_text("add_task_title"), 700, 600)
        
        # Khung chứa chính
        main_frame = ttk.Frame(top)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Vùng lựa chọn tệp
        file_frame = ttk.LabelFrame(main_frame, text=get_text("file_settings_label"), padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)

        # Tệp PDF
        ttk.Label(file_frame, text="Tệp PDF:").grid(row=0, column=0, sticky=tk.W, pady=8)
        pdf_var = tk.StringVar()
        pdf_entry = ttk.Entry(file_frame, textvariable=pdf_var)
        pdf_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")
        def browse_pdf():
            f = filedialog.askopenfilename(parent=top, title=get_text("select_pdf_title"), filetypes=[("PDF files", "*.pdf")])
            if f: pdf_var.set(f)
        ttk.Button(file_frame, text="Duyệt...", command=browse_pdf, width=8).grid(row=0, column=2, padx=5, pady=8)

        # Tệp JSON (Tùy chọn)
        ttk.Label(file_frame, text="Tệp JSON:").grid(row=1, column=0, sticky=tk.W, pady=8)
        json_var = tk.StringVar()
        json_entry = ttk.Entry(file_frame, textvariable=json_var)
        json_entry.grid(row=1, column=1, padx=5, pady=8, sticky="ew")
        def browse_json():
            f = filedialog.askopenfilename(parent=top, title=get_text("select_json_title"), filetypes=[("JSON files", "*.json")])
            if f: json_var.set(f)
        ttk.Button(file_frame, text="Duyệt...", command=browse_json, width=8).grid(row=1, column=2, padx=5, pady=8)
        ttk.Button(file_frame, text="Thông tin", command=self.show_mineru_info, width=6).grid(row=1, column=3, padx=2, pady=8)

        # Lấy cài đặt lần cuối của người dùng làm giá trị khởi tạo cho hộp thoại
        last_settings = getattr(self, 'last_task_settings', {})
        ttk.Button(file_frame, text="Thông tin", command=self.show_mineru_info, width=6).grid(row=1, column=3, padx=2, pady=8)

        # Thêm chức năng kéo thả cho cửa sổ hộp thoại
        if windnd:
            def on_dialog_drop(files):
                """Hàm xử lý kéo thả an toàn luồng - Sử dụng hàng đợi"""
                try:
                    self._drop_queue.put(('dialog', files, pdf_var, json_var))
                except:
                    pass
            
            try:
                windnd.hook_dropfiles(top, func=on_dialog_drop)
            except Exception as e:
                print(f"Khởi tạo chức năng kéo thả thất bại: {e}")

            # Khu vực tham số tác vụ - Sử dụng Canvas để hỗ trợ cuộn
        param_container = ttk.Frame(main_frame)
        param_container.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(param_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(param_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)

        # Khung tham số
        param_frame = ttk.LabelFrame(scrollable_frame, text=get_text("task_params_label"), padding="10")
        param_frame.pack(fill=tk.X, expand=False)
        param_frame.columnconfigure(1, weight=0)
        param_frame.columnconfigure(3, weight=0)

        # Hàng thứ nhất: DPI và tỷ lệ hiển thị
        ttk.Label(param_frame, text="DPI:").grid(row=0, column=0, sticky=tk.W, pady=8)
        dpi_var = tk.IntVar(value=last_settings.get('dpi', DEFAULT_TASK_SETTINGS['dpi']))
        dpi_entry = ttk.Entry(param_frame, textvariable=dpi_var, width=8)
        dpi_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=8)
        ttk.Label(param_frame, text="(150-300)", foreground="gray").grid(row=0, column=2, sticky=tk.W, padx=10)

        ttk.Label(param_frame, text="Tỷ lệ hiển thị:").grid(row=0, column=3, sticky=tk.W, padx=(20, 0))
        ratio_var = tk.DoubleVar(value=last_settings.get('ratio', DEFAULT_TASK_SETTINGS['ratio']))
        ratio_entry = ttk.Entry(param_frame, textvariable=ratio_var, width=8)
        ratio_entry.grid(row=0, column=4, sticky=tk.W, padx=5, pady=8)
        ttk.Label(param_frame, text="(0.7-0.9)", foreground="gray").grid(row=0, column=5, sticky=tk.W, padx=5)

        # Hàng thứ hai: Xóa hình mờ và phương pháp sửa chữa
        inpaint_var = tk.BooleanVar(value=last_settings.get('inpaint', DEFAULT_TASK_SETTINGS['inpaint']))
        ttk.Checkbutton(param_frame, text="Xóa hình mờ", variable=inpaint_var).grid(row=1, column=0, sticky=tk.W, pady=8)

        ttk.Label(param_frame, text="Phương pháp sửa chữa:").grid(row=1, column=2, sticky=tk.W, padx=10)
        # Sử dụng phương pháp sửa chữa lần trước (nếu có)
        last_method_id = last_settings.get('inpaint_method', '')
        try:
            last_method_translated = self.get_translated_name_from_id(last_method_id) if last_method_id else self.get_translated_method_names()[0]
        except:
            last_method_translated = self.get_translated_method_names()[0]
        inpaint_method_var = tk.StringVar(value=last_method_translated)
        inpaint_method_combo = ttk.Combobox(param_frame, textvariable=inpaint_method_var, width=20, state="readonly")
        inpaint_method_combo['values'] = self.get_translated_method_names()
        inpaint_method_combo.grid(row=1, column=3, columnspan=2, sticky=tk.W, padx=5, pady=8)
        ttk.Button(param_frame, text="Thông tin", command=self.show_inpaint_method_info, width=6).grid(row=1, column=5, padx=5, pady=8)

        # Hàng thứ ba: Chỉ chế độ hình ảnh và buộc tái tạo
        image_only_var = tk.BooleanVar(value=last_settings.get('image_only', DEFAULT_TASK_SETTINGS['image_only']))
        ttk.Checkbutton(param_frame, text="Chỉ chế độ hình ảnh", variable=image_only_var).grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=8)

        force_regenerate_var = tk.BooleanVar(value=last_settings.get('force_regenerate', DEFAULT_TASK_SETTINGS['force_regenerate']))
        ttk.Checkbutton(param_frame, text="Buộc tái tạo", variable=force_regenerate_var).grid(row=2, column=3, columnspan=3, sticky=tk.W, pady=8)

        # Hàng thứ tư: Phạm vi trang
        ttk.Label(param_frame, text="Phạm vi trang:").grid(row=3, column=0, sticky=tk.W, pady=8)
        page_range_var = tk.StringVar(value="")  # Phạm vi trang không được lưu
        page_range_entry = ttk.Entry(param_frame, textvariable=page_range_var, width=20)
        page_range_entry.grid(row=3, column=1, columnspan=2, sticky=tk.W, padx=5, pady=8)
        ttk.Label(param_frame, text="Ví dụ: 1-3,5", foreground="gray").grid(row=3, column=3, columnspan=2, sticky=tk.W, padx=10)

        # Hàng thứ năm: Tùy chọn unify font (chỉ hiển thị khi có JSON)
        font_frame = ttk.Frame(param_frame)
        unify_font_var = tk.BooleanVar(value=last_settings.get('unify_font', DEFAULT_TASK_SETTINGS['unify_font']))
        font_name_var = tk.StringVar(value=last_settings.get('font_name', DEFAULT_TASK_SETTINGS['font_name']))
        
        unify_check = ttk.Checkbutton(font_frame, text="Unify Font", variable=unify_font_var)
        unify_check.pack(side=tk.LEFT)
        ttk.Label(font_frame, text="Font:").pack(side=tk.LEFT, padx=(10, 2))
        font_entry = ttk.Entry(font_frame, textvariable=font_name_var, width=15)
        font_entry.pack(side=tk.LEFT, padx=5)

        def update_font_visibility(*args):
            if json_var.get().strip():
                font_frame.grid(row=4, column=0, columnspan=6, sticky=tk.W, pady=8, padx=0)
            else:
                font_frame.grid_forget()
        
        json_var.trace_add("write", update_font_visibility)
        update_font_visibility()

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Các nút ở dưới cùng
        btn_frame = ttk.Frame(top)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        def add_task_confirmed():
            pdf_path = pdf_var.get().strip().strip('"')
            if not pdf_path or not os.path.exists(pdf_path):
                messagebox.showerror(get_text("error_btn"), get_text("select_pdf_error"), parent=top)
                return
            
            json_path = json_var.get().strip().strip('"') or None
            if json_path and not os.path.exists(json_path):
                json_path = None
            
            # Thu thập tất cả tham số
            settings = {
                "output_dir": self.output_dir_var.get(),
                "dpi": dpi_var.get(),
                "ratio": ratio_var.get(),
                "inpaint": inpaint_var.get(),
                "inpaint_method": self.get_method_id_from_translated_name(inpaint_method_var.get()),  # Lưu ID phương pháp
                "image_only": image_only_var.get(),
                "force_regenerate": force_regenerate_var.get(),
                "unify_font": unify_font_var.get(),
                "font_name": font_name_var.get().strip() or "Calibri",
                "page_range": page_range_var.get().strip()
            }
            
            self.add_task_with_settings(pdf_path, json_path, settings)
            top.destroy()

        ttk.Button(btn_frame, text="Hủy", command=top.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Thêm tác vụ", command=add_task_confirmed).pack(side=tk.RIGHT, padx=5)

    def add_tasks_multi_pdfs(self):
        pdfs = filedialog.askopenfilenames(parent=self.root, title=get_text("select_pdf_title"), filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")])
        if not pdfs:
            return
        for p in pdfs:
            self.add_task(p, None)

    def add_tasks_batch_pair(self):
        """Hộp thoại để thêm nhiều tác vụ và ghép nối JSON"""
        top = self.create_toplevel(get_text("batch_add_dialog_title"), 1050, 950)
        
        # Các nút ở dưới cùng(Tạo trước, cố định ở dưới cùng)
        bottom_frame = ttk.Frame(top)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)
        
        # Tạo bộ chứa chính có thể cuộn (lấp đầy không gian còn lại)
        canvas = tk.Canvas(top, highlightthickness=0)
        scrollbar = ttk.Scrollbar(top, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Tự động điều chỉnh chiều rộng canvas
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        
        canvas.bind('<Configure>', on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Nội dung bộ chứa chính
        main_container = ttk.Frame(scrollable_frame, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # ============ Khu vực hướng dẫn quy trình ============
        guide_frame = ttk.Frame(main_container)
        guide_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Tiêu đề + Hướng dẫn
        title_frame = ttk.Frame(guide_frame)
        title_frame.pack(fill=tk.X)
        ttk.Label(title_frame, text=get_text("workflow_guide_title"), font=("TkDefaultFont", 10, "bold"), foreground="darkblue").pack(anchor=tk.W, pady=(0, 5))
        
        guide_text = (
            get_text("workflow_step1") + "\n" +
            get_text("workflow_step2") + "\n" +
            get_text("workflow_step3") + "\n" +
            get_text("workflow_step4")
        )
        ttk.Label(guide_frame, text=guide_text, foreground="darkslategray", wraplength=950).pack(anchor=tk.W, padx=10)
        
        ttk.Separator(main_container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        
        # Khu vực chọn tệp
        file_select_frame = ttk.LabelFrame(main_container, text=get_text("file_select_section"), padding="10")
        file_select_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Chọn PDF
        pdf_btn_frame = ttk.Frame(file_select_frame)
        pdf_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(pdf_btn_frame, text=get_text("select_pdf_btn"), command=lambda: self._batch_select_files(pdf_listbox, "pdf"), width=18).pack(side=tk.LEFT, padx=5)
        ttk.Label(pdf_btn_frame, text=get_text("pdf_hint"), foreground="gray").pack(side=tk.LEFT, padx=5)
        
        # Chọn JSON
        json_btn_frame = ttk.Frame(file_select_frame)
        json_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(json_btn_frame, text=get_text("select_json_btn"), command=lambda: self._batch_select_files(json_listbox, "json"), width=18).pack(side=tk.LEFT, padx=5)
        ttk.Label(json_btn_frame, text=get_text("json_hint"), foreground="gray").pack(side=tk.LEFT, padx=5)
        
        # Khu vực hiển thị ghép nối
        pair_frame = ttk.LabelFrame(main_container, text=get_text("pair_section"), padding="10")
        pair_frame.pack(fill=tk.BOTH, pady=(0, 10))
        pair_frame.configure(height=280)  # Giới hạn chiều cao khu vực ghép nối tệp
        pair_frame.columnconfigure(0, weight=1)
        pair_frame.columnconfigure(2, weight=1)
        
        # Danh sách PDF
        pdf_list_frame = ttk.Frame(pair_frame)
        pdf_list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        ttk.Label(pdf_list_frame, text=get_text("pdf_files_label"), font=("TkDefaultFont", 9, "bold")).pack()
        pdf_scroll = ttk.Scrollbar(pdf_list_frame)
        pdf_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        pdf_listbox = tk.Listbox(pdf_list_frame, yscrollcommand=pdf_scroll.set, selectmode=tk.SINGLE)
        pdf_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pdf_scroll.config(command=pdf_listbox.yview)
        
        # Các nút điều khiển ở giữa
        ctrl_frame = ttk.Frame(pair_frame)
        ctrl_frame.grid(row=0, column=1, padx=10)
        
        ttk.Label(ctrl_frame, text=get_text("adjust_order_label"), font=("TkDefaultFont", 8)).pack(pady=(20, 5))
        ttk.Button(ctrl_frame, text="↑", width=4, command=lambda: self._move_item_up(pdf_listbox)).pack(pady=2)
        ttk.Button(ctrl_frame, text="↓", width=4, command=lambda: self._move_item_down(pdf_listbox)).pack(pady=2)
        
        ttk.Separator(ctrl_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        ttk.Label(ctrl_frame, text=get_text("pairing_label"), font=("TkDefaultFont", 8)).pack(pady=5)
        ttk.Button(ctrl_frame, text=get_text("pair_btn"), width=4, command=lambda: self._pair_files(pdf_listbox, json_listbox, pair_display)).pack(pady=2)
        ttk.Button(ctrl_frame, text=get_text("clear_pairing_btn"), width=4, command=lambda: self._clear_pairing(pdf_listbox, json_listbox, pair_display)).pack(pady=2)
        
        ttk.Separator(ctrl_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        ttk.Label(ctrl_frame, text=get_text("json_order_label"), font=("TkDefaultFont", 8)).pack(pady=5)
        ttk.Button(ctrl_frame, text="↑", width=4, command=lambda: self._move_item_up(json_listbox)).pack(pady=2)
        ttk.Button(ctrl_frame, text="↓", width=4, command=lambda: self._move_item_down(json_listbox)).pack(pady=2)
        
        # Danh sách JSON
        json_list_frame = ttk.Frame(pair_frame)
        json_list_frame.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        ttk.Label(json_list_frame, text=get_text("json_files_label"), font=("TkDefaultFont", 9, "bold")).pack()
        json_scroll = ttk.Scrollbar(json_list_frame)
        json_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        json_listbox = tk.Listbox(json_list_frame, yscrollcommand=json_scroll.set, selectmode=tk.SINGLE)
        json_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        json_scroll.config(command=json_listbox.yview)
        
        pair_frame.rowconfigure(0, weight=1)
        
        # Khu vực hiển thị trạng thái ghép nối (phiên bản ngắn gọn)
        status_frame = ttk.Frame(main_container)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        status_label = ttk.Label(
            status_frame, 
            text=get_text("status_waiting"),
            font=("", 9),
            foreground="gray",
            wraplength=950
        )
        status_label.pack(anchor=tk.W, padx=5, pady=5)
        
        # Từ điển lưu trữ các mối quan hệ ghép nối: {pdf_path: json_path or None}
        pairing_dict = {}
        
        # Hàm trợ giúp: Đồng bộ hóa kích thước của hai Listbox (xử lý thông minh phần giữ chỗ)
        def sync_listbox_sizes():
            # Thu thập tất cả các tệp thực
            real_pdfs = []
            real_jsons = []
            
            for i in range(pdf_listbox.size()):
                item = pdf_listbox.get(i)
                if not item.startswith("[Không"):
                    real_pdfs.append(item)
            
            for i in range(json_listbox.size()):
                item = json_listbox.get(i)
                if not item.startswith("[Không"):
                    real_jsons.append(item)
            
            # Xóa cả hai danh sách
            pdf_listbox.delete(0, tk.END)
            json_listbox.delete(0, tk.END)
            
            # Điền lại, đảm bảo chiều dài nhất quán
            max_count = max(len(real_pdfs), len(real_jsons))
            
            for i in range(max_count):
                if i < len(real_pdfs):
                    pdf_listbox.insert(tk.END, real_pdfs[i])
                else:
                    pdf_listbox.insert(tk.END, "[Không có PDF]")
                
                if i < len(real_jsons):
                    json_listbox.insert(tk.END, real_jsons[i])
                else:
                    json_listbox.insert(tk.END, "[Không có JSON]")
            
            # Cập nhật từ điển ghép nối: chỉ giữ các ghép nối hiện có, PDF mới được khởi tạo là chưa ghép nối
            new_pairing = {}
            for i in range(max_count):
                pdf = pdf_listbox.get(i) if i < pdf_listbox.size() else None
                
                # Chỉ xử lý các tệp PDF thực
                if pdf and not pdf.startswith("[Không"):
                    # Nếu PDF đó đã có trong pairing_dict, hãy giữ ghép nối ban đầu của nó; nếu không, hãy khởi tạo thành None (chưa ghép nối)
                    if pdf in pairing_dict:
                        new_pairing[pdf] = pairing_dict[pdf]
                    else:
                        new_pairing[pdf] = None
            
            pairing_dict.clear()
            pairing_dict.update(new_pairing)
        
        # Hàm trợ giúp: Cập nhật hiển thị trạng thái ghép nối
        def update_pair_display():
            if not pairing_dict:
                status_label.config(
                    text=get_text("status_waiting"),
                    foreground="gray"
                )
            else:
                with_json = sum(1 for v in pairing_dict.values() if v)
                without_json = len(pairing_dict) - with_json
                
                # Đếm số lượng tệp JSON (loại trừ phần giữ chỗ)
                json_count = 0
                for i in range(json_listbox.size()):
                    item = json_listbox.get(i)
                    if not item.startswith("[Không"):
                        json_count += 1
                
                if with_json == len(pairing_dict):
                    msg = get_text("status_all_paired", count=len(pairing_dict))
                    color = "darkgreen"
                elif with_json == 0 and json_count > 0:
                    # Có JSON nhưng chưa ghép nối
                    msg = get_text("status_no_paired_but_has_json", pdf_count=len(pairing_dict), json_count=json_count)
                    color = "darkorange"
                elif with_json == 0:
                    # Không có JSON và chưa ghép nối
                    msg = get_text("status_no_paired", count=len(pairing_dict))
                    color = "darkorange"
                else:
                    msg = get_text("status_partial_paired", with_json=with_json, without_json=without_json)
                    color = "darkblue"
                
                status_label.config(text=msg, foreground=color)
        
        # Hàm trợ giúp chọn tệp
        def select_files_helper(listbox, file_type):
            if file_type == "pdf":
                files = filedialog.askopenfilenames(
                    parent=top,
                    title="Chọn tệp PDF",
                    filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
                )
            else:
                files = filedialog.askopenfilenames(
                    parent=top,
                    title="Chọn tệp JSON",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
                )
            
            if files:
                for f in files:
                    if f not in listbox.get(0, tk.END):
                        listbox.insert(tk.END, f)
                        if file_type == "pdf" and f not in pairing_dict:
                            pairing_dict[f] = None
                sync_listbox_sizes()
                update_pair_display()
        
        # Liên kết các hàm trợ giúp với toàn cầu (để sử dụng lambda)
        self._batch_select_files = select_files_helper
        
        # Thêm chức năng kéo thả cho PDF listbox
        if windnd:
            def on_pdf_drop(files):
                """Xử lý kéo thả PDF an toàn luồng - Sử dụng hàng đợi"""
                try:
                    self._drop_queue.put(('pdf', files, pdf_listbox, pairing_dict, sync_listbox_sizes, update_pair_display))
                except:
                    pass
            
            try:
                windnd.hook_dropfiles(pdf_listbox, func=on_pdf_drop)
            except Exception as e:
                print(f"PDFKhởi tạo chức năng kéo thả thất bại: {e}")
        
        # Thêm chức năng kéo thả cho JSON listbox
        if windnd:
            def on_json_drop(files):
                """Xử lý kéo thả JSON an toàn luồng - Sử dụng hàng đợi"""
                try:
                    self._drop_queue.put(('json', files, json_listbox, pairing_dict, sync_listbox_sizes, update_pair_display))
                except:
                    pass
            
            try:
                windnd.hook_dropfiles(json_listbox, func=on_json_drop)
            except Exception as e:
                print(f"JSONKhởi tạo chức năng kéo thả thất bại: {e}")
        
        # Khu vực nút dưới - Chia thành vùng ghép nối tự động và vùng hoạt động
        ttk.Separator(main_container, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        
        # Khu vực ghép nối tự động (nổi bật)
        auto_pair_frame = ttk.LabelFrame(main_container, text=get_text("auto_pair_section"), padding="10", relief="solid", borderwidth=2)
        auto_pair_frame.pack(fill=tk.X, pady=(0, 10))
        
        auto_pair_info = ttk.Label(
            auto_pair_frame, 
            text=get_text("auto_pair_desc"),
            wraplength=950
        )
        auto_pair_info.pack(anchor=tk.W, pady=(0, 8))
        
        auto_pair_btns = ttk.Frame(auto_pair_frame)
        auto_pair_btns.pack(fill=tk.X)
        
        ttk.Button(
            auto_pair_btns, 
            text=get_text("smart_pair_btn"), 
            command=lambda: self._auto_pair_by_similarity(pdf_listbox, json_listbox, pairing_dict, update_pair_display),
            width=20
        ).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(auto_pair_btns, text=get_text("smart_pair_desc"), foreground="darkgreen").pack(side=tk.LEFT, padx=5)
        
        auto_pair_btns2 = ttk.Frame(auto_pair_frame)
        auto_pair_btns2.pack(fill=tk.X)
        
        ttk.Button(
            auto_pair_btns2, 
            text=get_text("order_pair_btn"), 
            command=lambda: self._auto_pair_by_order(pdf_listbox, json_listbox, pairing_dict, update_pair_display),
            width=20
        ).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Label(auto_pair_btns2, text=get_text("order_pair_desc"), foreground="darkgreen").pack(side=tk.LEFT, padx=5)
        
        # Nội dung nút hoạt động ở dưới (sử dụng bottom_frame được tạo trước đó)
        def add_all_tasks():
            if not pairing_dict:
                messagebox.showwarning(get_text("info_btn"), get_text("no_pdf_warning"), parent=top)
                return
            
            # Kiểm tra xem có JSON nhưng chưa ghép nối
            with_json = sum(1 for v in pairing_dict.values() if v)
            
            # Đếm số lượng tệp JSON (loại trừ phần giữ chỗ)
            json_count = 0
            for i in range(json_listbox.size()):
                item = json_listbox.get(i)
                if not item.startswith("[Không"):
                    json_count += 1
            
            # Nếu có JSON nhưng chưa ghép nối, nhắc nhở người dùng phải ghép nối trước
            if json_count > 0 and with_json == 0:
                messagebox.showwarning(
                    get_text("info_btn"), 
                    get_text("json_not_paired_warning", json_count=json_count), 
                    parent=top
                )
                return
            
            # Hiển thị hộp thoại thiết lập tham số
            self.show_batch_task_params_dialog(pairing_dict, top)
        
        # Bên trái: Hủy
        ttk.Button(bottom_frame, text="❌ " + get_text("cancel_btn"), command=top.destroy).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Bên phải: Thêm tác vụ
        ttk.Button(
            bottom_frame, 
            text=get_text("add_all_tasks_btn"), 
            command=add_all_tasks,
            width=18
        ).pack(side=tk.RIGHT, padx=5, pady=5)
        
        update_pair_display()

    def _handle_dialog_drop_files_impl(self, files, pdf_var, json_var):
        """Phiên bản an toàn luồng cho xử lý kéo thả tệp trong hộp thoại"""
        try:
            if not files:
                return
            
            decoded_files = []
            for f in files:
                try:
                    decoded_files.append(f.decode('gbk') if isinstance(f, bytes) else f)
                except:
                    decoded_files.append(f.decode('utf-8', errors='ignore') if isinstance(f, bytes) else f)
            
            pdfs = [f for f in decoded_files if f.lower().endswith('.pdf')]
            jsons = [f for f in decoded_files if f.lower().endswith('.json')]
            
            if pdfs and not pdf_var.get():
                pdf_var.set(pdfs[0])
                print(f"Đã thêm tệp PDF: {pdfs[0]}")
            
            if jsons and not json_var.get():
                json_var.set(jsons[0])
                print(f"Đã thêm tệp JSON: {jsons[0]}")
                
        except Exception as e:
            print(f"Lỗi khi xử lý tệp kéo thả: {e}")
    
    def _handle_batch_pdf_drop(self, files, pdf_listbox, pairing_dict, sync_func, update_func):
        """Phiên bản an toàn luồng cho xử lý kéo thả PDF hàng loạt"""
        try:
            if not files:
                return
            
            decoded_files = []
            for f in files:
                try:
                    decoded_files.append(f.decode('gbk') if isinstance(f, bytes) else f)
                except:
                    decoded_files.append(f.decode('utf-8', errors='ignore') if isinstance(f, bytes) else f)
            
            pdfs = [f for f in decoded_files if f.lower().endswith('.pdf')]
            
            if pdfs:
                for pdf in pdfs:
                    if pdf not in [pdf_listbox.get(i) for i in range(pdf_listbox.size())]:
                        pdf_listbox.insert(tk.END, pdf)
                        pairing_dict[pdf] = None
                
                sync_func()
                update_func()
                print(f"Đã thêm {len(pdfs)} tệp PDF")
            else:
                print("Vui lòng kéo thả tệp PDF")
                
        except Exception as e:
            print(f"Lỗi khi xử lý kéo thả PDF: {e}")
    
    def _handle_batch_json_drop(self, files, json_listbox, pairing_dict, sync_func, update_func):
        """Phiên bản an toàn luồng cho xử lý kéo thả JSON hàng loạt"""
        try:
            if not files:
                return
            
            decoded_files = []
            for f in files:
                try:
                    decoded_files.append(f.decode('gbk') if isinstance(f, bytes) else f)
                except:
                    decoded_files.append(f.decode('utf-8', errors='ignore') if isinstance(f, bytes) else f)
            
            jsons = [f for f in decoded_files if f.lower().endswith('.json')]
            
            if jsons:
                for json_file in jsons:
                    if json_file not in [json_listbox.get(i) for i in range(json_listbox.size())]:
                        json_listbox.insert(tk.END, json_file)
                
                sync_func()
                update_func()
                print(f"Đã thêm {len(jsons)} tệp JSON")
            else:
                print("Vui lòng kéo thả tệp JSON")
                
        except Exception as e:
            print(f"Lỗi khi xử lý kéo thả JSON: {e}")

    def _move_item_up(self, listbox):
        """Di chuyển mục đã chọn lên trên"""
        selection = listbox.curselection()
        if not selection or selection[0] == 0:
            return
        idx = selection[0]
        item = listbox.get(idx)
        listbox.delete(idx)
        listbox.insert(idx - 1, item)
        listbox.selection_set(idx - 1)

    def _move_item_down(self, listbox):
        """Di chuyển mục đã chọn xuống dưới"""
        selection = listbox.curselection()
        if not selection or selection[0] == listbox.size() - 1:
            return
        idx = selection[0]
        item = listbox.get(idx)
        listbox.delete(idx)
        listbox.insert(idx + 1, item)
        listbox.selection_set(idx + 1)

    def show_batch_task_params_dialog(self, pairing_dict, parent_window):
        """Hiển thị hộp thoại cài đặt tham số chung cho tác vụ hàng loạt"""
        param_top = self.create_toplevel(get_text("batch_params_title"), 700, 600)
        
        # Bộ chứa chính
        main_frame = ttk.Frame(param_top)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Lấy cài đặt lần cuối của người dùng làm giá trị khởi tạo cho tác vụ hàng loạt
        last_settings = getattr(self, 'last_task_settings', {})
        
        # Khu vực tham số tác vụ - Sử dụng Canvas để hỗ trợ cuộn
        param_container = ttk.Frame(main_frame)
        param_container.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(param_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(param_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)

        # Khung tham số
        param_frame = ttk.LabelFrame(scrollable_frame, text=get_text("task_params_label"), padding="10")
        param_frame.pack(fill=tk.X, expand=False)
        param_frame.columnconfigure(1, weight=0)
        param_frame.columnconfigure(3, weight=0)

        # Hàng thứ nhất: DPI và tỷ lệ hiển thị
        ttk.Label(param_frame, text="DPI:").grid(row=0, column=0, sticky=tk.W, pady=8)
        dpi_var = tk.IntVar(value=last_settings.get('dpi', DEFAULT_TASK_SETTINGS['dpi']))
        dpi_entry = ttk.Entry(param_frame, textvariable=dpi_var, width=8)
        dpi_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=8)
        ttk.Label(param_frame, text="(150-300)", foreground="gray").grid(row=0, column=2, sticky=tk.W, padx=10)

        ttk.Label(param_frame, text="Tỷ lệ hiển thị:").grid(row=0, column=3, sticky=tk.W, padx=(20, 0))
        ratio_var = tk.DoubleVar(value=last_settings.get('ratio', DEFAULT_TASK_SETTINGS['ratio']))
        ratio_entry = ttk.Entry(param_frame, textvariable=ratio_var, width=8)
        ratio_entry.grid(row=0, column=4, sticky=tk.W, padx=5, pady=8)
        ttk.Label(param_frame, text="(0.7-0.9)", foreground="gray").grid(row=0, column=5, sticky=tk.W, padx=5)

        # Hàng thứ hai: Xóa hình mờ và phương pháp sửa chữa
        inpaint_var = tk.BooleanVar(value=last_settings.get('inpaint', DEFAULT_TASK_SETTINGS['inpaint']))
        ttk.Checkbutton(param_frame, text="Xóa hình mờ", variable=inpaint_var).grid(row=1, column=0, sticky=tk.W, pady=8)

        ttk.Label(param_frame, text="Phương pháp sửa chữa:").grid(row=1, column=2, sticky=tk.W, padx=10)
        # Sử dụng phương pháp sửa chữa lần trước
        last_method_id = last_settings.get('inpaint_method', '')
        try:
            last_method_translated = self.get_translated_name_from_id(last_method_id) if last_method_id else self.get_translated_method_names()[0]
        except:
            last_method_translated = self.get_translated_method_names()[0]
        inpaint_method_var = tk.StringVar(value=last_method_translated)
        inpaint_method_combo = ttk.Combobox(param_frame, textvariable=inpaint_method_var, width=20, state="readonly")
        inpaint_method_combo['values'] = self.get_translated_method_names()
        inpaint_method_combo.grid(row=1, column=3, columnspan=2, sticky=tk.W, padx=5, pady=8)
        ttk.Button(param_frame, text="Thông tin", command=self.show_inpaint_method_info, width=6).grid(row=1, column=5, padx=5, pady=8)

        # Hàng thứ ba: Chỉ chế độ hình ảnh và buộc tái tạo
        image_only_var = tk.BooleanVar(value=last_settings.get('image_only', DEFAULT_TASK_SETTINGS['image_only']))
        ttk.Checkbutton(param_frame, text="Chỉ chế độ hình ảnh", variable=image_only_var).grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=8)

        force_regenerate_var = tk.BooleanVar(value=last_settings.get('force_regenerate', DEFAULT_TASK_SETTINGS['force_regenerate']))
        ttk.Checkbutton(param_frame, text="Buộc tái tạo", variable=force_regenerate_var).grid(row=2, column=3, columnspan=3, sticky=tk.W, pady=8)

        # Hàng thứ tư: Phạm vi trang
        ttk.Label(param_frame, text="Phạm vi trang:").grid(row=3, column=0, sticky=tk.W, pady=8)
        page_range_var = tk.StringVar(value="")  # Phạm vi trang không được lưu cho tác vụ hàng loạt
        page_range_entry = ttk.Entry(param_frame, textvariable=page_range_var, width=20)
        page_range_entry.grid(row=3, column=1, columnspan=2, sticky=tk.W, padx=5, pady=8)
        ttk.Label(param_frame, text="Ví dụ: 1-3,5", foreground="gray").grid(row=3, column=3, columnspan=2, sticky=tk.W, padx=10)

        # Hàng thứ năm: Tùy chọn thống nhất phông chữ
        font_frame = ttk.Frame(param_frame)
        unify_font_var = tk.BooleanVar(value=last_settings.get('unify_font', DEFAULT_TASK_SETTINGS['unify_font']))
        font_name_var = tk.StringVar(value=last_settings.get('font_name', DEFAULT_TASK_SETTINGS['font_name']))
        
        unify_check = ttk.Checkbutton(font_frame, text="Unify Font", variable=unify_font_var)
        unify_check.pack(side=tk.LEFT)
        ttk.Label(font_frame, text="Font:").pack(side=tk.LEFT, padx=(10, 2))
        font_entry = ttk.Entry(font_frame, textvariable=font_name_var, width=15)
        font_entry.pack(side=tk.LEFT, padx=5)
        font_frame.grid(row=4, column=0, columnspan=6, sticky=tk.W, pady=8, padx=0)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Các nút ở dưới cùng
        btn_frame = ttk.Frame(param_top)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        def confirm_and_add():
            # Thu thập tất cả tham số
            settings = {
                "output_dir": self.output_dir_var.get(),
                "dpi": dpi_var.get(),
                "ratio": ratio_var.get(),
                "inpaint": inpaint_var.get(),
                "inpaint_method": self.get_method_id_from_translated_name(inpaint_method_var.get()),  # Lưu ID phương pháp
                "image_only": image_only_var.get(),
                "force_regenerate": force_regenerate_var.get(),
                "unify_font": unify_font_var.get(),
                "font_name": font_name_var.get().strip() or "Calibri",
                "page_range": page_range_var.get().strip()
            }
            
            # Thống kê tình trạng ghép cặp
            with_json = sum(1 for v in pairing_dict.values() if v)
            without_json = len(pairing_dict) - with_json
            
            # Thêm tác vụ hàng loạt (bỏ qua phần giữ chỗ)
            for pdf, json_path in pairing_dict.items():
                if not pdf.startswith("[Không"):
                    self.add_task_with_settings(pdf, json_path, settings)
            
            # Hiển thị kết quả thêm
            if with_json == len(pairing_dict):
                msg = f"Đã thêm {len(pairing_dict)} tác vụ (tất cả đã ghép cặp JSON)"
            elif with_json == 0:
                msg = f"Đã thêm {len(pairing_dict)} tác vụ (không có JSON)"
            else:
                msg = f"Đã thêm {len(pairing_dict)} tác vụ\n• {with_json} đã ghép cặp JSON\n• {without_json} không có JSON"
            
            messagebox.showinfo("Thành công", msg, parent=param_top)
            param_top.destroy()
            parent_window.destroy()

        ttk.Button(btn_frame, text="Hủy", command=param_top.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Xác nhận và thêm tác vụ", command=confirm_and_add).pack(side=tk.RIGHT, padx=5)

    def _pair_files(self, pdf_listbox, json_listbox, pair_display):
        """Ghép nối PDF và JSON đã chọn"""
        pdf_sel = pdf_listbox.curselection()
        json_sel = json_listbox.curselection()
        
        if not pdf_sel:
            messagebox.showwarning("Thông báo", "Vui lòng chọn một tệp PDF trước")
            return
        
        pdf_path = pdf_listbox.get(pdf_sel[0])
        json_path = json_listbox.get(json_sel[0]) if json_sel else None
        
        # Cập nhật từ điển ghép cặp (truy cập qua closure)
        # Cần truy cập `pairing_dict` từ bên ngoài, nên điều chỉnh cách triển khai
        # Tạm thời sử dụng `itemconfig` của listbox để đánh dấu
        pass

    def _clear_pairing(self, pdf_listbox, json_listbox, pair_display):
        """Xóa ghép cặp của PDF đã chọn"""
        pdf_sel = pdf_listbox.curselection()
        if not pdf_sel:
            return
        # Thực hiện logic xóa ghép cặp
        pass

    def _auto_pair_by_order(self, pdf_listbox, json_listbox, pairing_dict, update_callback):
        """Ghép tự động theo thứ tự"""
        # Thu thập các file thực
        real_pdfs = []
        real_jsons = []
        
        for i in range(pdf_listbox.size()):
            pdf = pdf_listbox.get(i)
            if not pdf.startswith("[Không"):
                real_pdfs.append(pdf)
        
        for i in range(json_listbox.size()):
            json_path = json_listbox.get(i)
            if not json_path.startswith("[Không"):
                real_jsons.append(json_path)
        
        # Ghép theo thứ tự
        pairing_dict.clear()
        paired_count = 0
        
        for i, pdf in enumerate(real_pdfs):
            json_path = real_jsons[i] if i < len(real_jsons) else None
            pairing_dict[pdf] = json_path
            if json_path:
                paired_count += 1
        
        # Sắp xếp lại hai danh sách để hiển thị kết quả ghép cặp rõ ràng
        pdf_listbox.delete(0, tk.END)
        json_listbox.delete(0, tk.END)
        
        # Thêm file theo thứ tự ghép cặp
        max_count = max(len(real_pdfs), len(real_jsons))
        for i in range(max_count):
            if i < len(real_pdfs):
                pdf_listbox.insert(tk.END, real_pdfs[i])
            else:
                pdf_listbox.insert(tk.END, "[Không có PDF]")
            
            if i < len(real_jsons):
                json_listbox.insert(tk.END, real_jsons[i])
            else:
                json_listbox.insert(tk.END, "[Không có JSON]")
        
        update_callback()
        
        # Hiển thị kết quả ghép chi tiết
        pdf_real_count = len(real_pdfs)
        if paired_count == pdf_real_count and pdf_real_count > 0:
            msg = get_text("order_pair_complete_all", count=pdf_real_count)
        elif paired_count == 0:
            msg = get_text("order_pair_complete_none", count=pdf_real_count)
        else:
            unpaired_count = pdf_real_count - paired_count
            msg = get_text("order_pair_complete_partial", paired=paired_count, unpaired=unpaired_count)
        
        messagebox.showinfo(get_text("order_pair_title"), msg, parent=pdf_listbox.master.master.master)

    def _auto_pair_by_name(self, pdf_listbox, json_listbox, pairing_dict, update_callback):
        """Ghép tự động theo tên file (khớp stem)"""
        # Đồng bộ kích thước danh sách (chèn placeholder)
        pdf_count = pdf_listbox.size()
        json_count = json_listbox.size()
        
        if pdf_count > json_count:
            for i in range(json_count, pdf_count):
                json_listbox.insert(tk.END, "[Không có JSON]")
        elif json_count > pdf_count:
            for i in range(pdf_count, json_count):
                pdf_listbox.insert(tk.END, "[Không có PDF]")
        
        pairing_dict.clear()

        # Tạo ánh xạ từ tên tệp JSON sang đường dẫn
        json_map = {}
        for i in range(json_listbox.size()):
            json_path = json_listbox.get(i)
            if not json_path.startswith("[Không"):
                stem = Path(json_path).stem
                json_map[stem] = json_path
        
        # Tìm JSON khớp cho mỗi PDF
        matched = 0
        for i in range(pdf_listbox.size()):
            pdf = pdf_listbox.get(i)
            if not pdf.startswith("[Không"):
                pdf_stem = Path(pdf).stem
                json_path = json_map.get(pdf_stem)
                pairing_dict[pdf] = json_path
                if json_path:
                    matched += 1
        
        update_callback()
        messagebox.showinfo("Hoàn tất ghép", f"Đã ghép {matched}/{len(pairing_dict)} file", parent=pdf_listbox.master.master.master)

    def _auto_pair_by_similarity(self, pdf_listbox, json_listbox, pairing_dict, update_callback):
        """Ghép thông minh dựa trên độ tương đồng tên tệp"""
        # Đồng bộ kích thước danh sách (chèn placeholder)
        pdf_count = pdf_listbox.size()
        json_count = json_listbox.size()
        
        if pdf_count > json_count:
            for i in range(json_count, pdf_count):
                json_listbox.insert(tk.END, "[Không có JSON]")
        elif json_count > pdf_count:
            for i in range(pdf_count, json_count):
                pdf_listbox.insert(tk.END, "[Không có PDF]")
        
        pairing_dict.clear()

        # Thu thập tất cả PDF và JSON thực
        real_pdfs = []
        real_jsons = []
        
        for i in range(pdf_listbox.size()):
            pdf = pdf_listbox.get(i)
            if not pdf.startswith("[Không"):
                real_pdfs.append(pdf)
        
        for i in range(json_listbox.size()):
            json_path = json_listbox.get(i)
            if not json_path.startswith("[Không"):
                real_jsons.append(json_path)
        
        # Ghép bằng thuật toán tương đồng
        matched = 0
        used_jsons = set()
        
        for pdf in real_pdfs:
            pdf_stem = Path(pdf).stem.lower()
            best_match = None
            best_score = 0
            
            # Tìm JSON tương đồng nhất cho mỗi PDF
            for json_path in real_jsons:
                if json_path in used_jsons:
                    continue
                
                json_stem = Path(json_path).stem.lower()
                
                # Tính toán độ tương đồng
                similarity = difflib.SequenceMatcher(None, pdf_stem, json_stem).ratio()

                if similarity > best_score and similarity > 0.3:  # Thiết lập ngưỡng tương đồng tối thiểu
                    best_score = similarity
                    best_match = json_path
            
            # Kết quả ghép đôi
            if best_match:
                pairing_dict[pdf] = best_match
                used_jsons.add(best_match)
                matched += 1
            else:
                pairing_dict[pdf] = None
        
        # Sắp xếp lại hai danh sách để hiển thị kết quả ghép đôi
        pdf_listbox.delete(0, tk.END)
        json_listbox.delete(0, tk.END)
        
        # Thêm các tệp đã ghép đôi trước
        for pdf, json_path in pairing_dict.items():
            if json_path:  # Có JSON đã ghép đôi
                pdf_listbox.insert(tk.END, pdf)
                json_listbox.insert(tk.END, json_path)
        
        # Sau đó thêm PDF chưa ghép đôi
        for pdf, json_path in pairing_dict.items():
            if not json_path:  # Không có JSON ghép đôi
                pdf_listbox.insert(tk.END, pdf)
                json_listbox.insert(tk.END, "[Không có JSON]")
        
        # Thêm các tệp JSON chưa sử dụng (nếu có)
        unused_jsons = [j for j in real_jsons if j not in used_jsons]
        for json_path in unused_jsons:
            pdf_listbox.insert(tk.END, "[Không có PDF]")
            json_listbox.insert(tk.END, json_path)
        
        update_callback()
        
        # Hiển thị thống kê kết quả ghép đôi
        total_pdfs = len(real_pdfs)
        if matched == total_pdfs and total_pdfs > 0:
            msg = get_text("smart_pair_complete_all", count=total_pdfs)
        elif matched == 0:
            msg = get_text("smart_pair_complete_none", count=total_pdfs)
        else:
            unmatched = total_pdfs - matched
            msg = get_text("smart_pair_complete_partial", matched=matched, unmatched=unmatched)
        
        messagebox.showinfo(get_text("smart_pair_title"), msg, parent=pdf_listbox.master.master.master)

    def remove_selected_task(self):
        sel = self.queue_tree.selection()
        if not sel:
            return
        for iid in sel:
            tid = int(iid)
            self.queue_tree.delete(iid)
            self.task_queue = [t for t in self.task_queue if t["id"] != tid]
        print(get_text("queue_task_removed"))

    def clear_tasks(self):
        for item in self.queue_tree.get_children():
            self.queue_tree.delete(item)
        self.task_queue = []
        print(get_text("queue_cleared"))

    def on_task_double_click(self, event):
        item_id = self.queue_tree.identify_row(event.y)
        if not item_id:
            return
        
        # item_id is stored as string of task id
        try:
            task_id = int(item_id)
        except ValueError:
            return

        task = next((t for t in self.task_queue if t["id"] == task_id), None)
        if not task:
            return

        self.show_task_details(task)

    def show_task_details(self, task):
        # Giảm chiều cao mặc định xuống 650, giữ chiều rộng 700 để phù hợp nhiều màn hình hơn
        top = self.create_toplevel(get_text("task_details_title"), 700, 650)
        
        # Tạo khung chứa chính
        content_frame = ttk.Frame(top)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sử dụng Canvas và Scrollbar để hỗ trợ cuộn
        canvas = tk.Canvas(content_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Cho khung nội thất thay đổi theo Canvas để tránh che khuất nội dung
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(canvas_window, width=e.width))
        
        canvas.configure(yscrollcommand=scrollbar.set)

        info_frame = ttk.LabelFrame(scrollable_frame, text=get_text("queue_label"), padding="10")
        info_frame.pack(fill=tk.X, expand=False, padx=10, pady=5)
        
        # Lưu trữ các biến có thể chỉnh sửa
        edit_vars = {}

        # Helper để tạo hàng (chỉ đọc)
        def add_readonly_row(parent, label_key, value, row, is_path=False):
            # Tăng chiều rộng nhãn lên 120, bỏ giới hạn xuống dòng để bố cục thoáng hơn
            ttk.Label(parent, text=get_text(label_key), font=("", 9, "bold"), width=20).grid(row=row, column=0, sticky="nw", pady=5)
            val_frame = ttk.Frame(parent)
            val_frame.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
            
            display_value = str(value) if value is not None else get_text("none")
            
            # Dùng height lớn hơn để hiển thị đường dẫn dài, width đặt 10 và dùng expand để lấp đầy
            txt = tk.Text(val_frame, height=3 if is_path else 1, width=10, wrap=tk.WORD, borderwidth=0, bg=top.cget("bg"), font=("", 9))
            txt.insert("1.0", display_value)
            txt.configure(state="disabled")
            txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            if is_path and value and os.path.exists(value):
                def open_path():
                    try:
                        os.startfile(value)
                    except Exception:
                        pass
                ttk.Button(val_frame, text=get_text("open_btn"), command=open_path, width=6).pack(side=tk.LEFT, padx=5)

        info_frame.columnconfigure(1, weight=1)
        
        # Kiểm tra nhiệm vụ có thể chỉnh sửa hay không (chỉ nhiệm vụ chưa bắt đầu hoặc gặp lỗi mới có thể)
        is_editable = task["status"] not in [get_text("queue_status_done"), get_text("queue_status_running")]
        
        # Thống nhất màu khi khóa: dùng Entry readonly và đặt readonlybackground bằng màu nền cửa sổ để chữ rõ ràng
        # Dù ở trạng thái vô hiệu hóa, vẫn đảm bảo màu chữ là đen hoặc xám đậm
        style = ttk.Style()
        style.configure("ReadOnly.TEntry", fieldbackground=top.cget("bg"), foreground="black")
        style.configure("ReadOnly.TCombobox", fieldbackground=top.cget("bg"), foreground="black")

        widget_state = "normal" if is_editable else "disabled"
        entry_state = "normal" if is_editable else "readonly"

        add_readonly_row(info_frame, "queue_col_id", task["id"], 0)
        add_readonly_row(info_frame, "queue_col_status", task["status"], 1)
        add_readonly_row(info_frame, "queue_col_pdf", task["pdf"], 2, is_path=True)
        
        # Cho phép chỉnh sửa đường dẫn JSON
        ttk.Label(info_frame, text=get_text("queue_col_json"), font=("", 9, "bold"), width=20).grid(row=3, column=0, sticky="nw", pady=5)
        json_frame = ttk.Frame(info_frame)
        json_frame.grid(row=3, column=1, sticky="ew", padx=10, pady=5)
        json_var = tk.StringVar(value=task["json"] or "")
        ttk.Entry(json_frame, textvariable=json_var, state=entry_state, style="ReadOnly.TEntry" if not is_editable else "").pack(side=tk.LEFT, fill=tk.X, expand=True)
        def browse_json():
            f = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
            if f: json_var.set(f)
        ttk.Button(json_frame, text=get_text("browse_btn"), command=browse_json, width=6, state=widget_state).pack(side=tk.LEFT, padx=5)

        # Hiển thị file đầu ra (hiển thị một hoặc hai file tùy có phiên bản tối ưu hay không)
        unoptimized_output = task.get("output_unoptimized", "")
        optimized_output = task.get("output_optimized", "")
        
        if optimized_output:
            # Hiển thị phiên bản đã tối ưu
            add_readonly_row(info_frame, "queue_col_output_optimized", optimized_output, 4, is_path=True)
            # Hiển thị phiên bản chưa tối ưu
            add_readonly_row(info_frame, "queue_col_output_unoptimized", unoptimized_output, 5, is_path=True)
        else:
            # Chỉ hiển thị một file đầu ra
            add_readonly_row(info_frame, "queue_col_output", unoptimized_output or task.get("output", ""), 4, is_path=True)

        # Khu vực cài đặt - có thể chỉnh sửa
        settings = task.get("settings", {})
        # Ngay cả khi không có settings, khởi tạo dict rỗng để có thể chỉnh sửa (về lý thuyết task mới luôn có)
        if settings is None:
            settings = {}
        
        # Cung cấp giá trị mặc định cho các task cũ
        default_settings = get_default_settings(
            output_dir=self.output_dir_var.get() if hasattr(self, 'output_dir_var') else "workspace",
            inpaint_method="background_smooth"
        )
        # Gộp giá trị mặc định và giá trị thực tế
        for key, default_val in default_settings.items():
            if key not in settings or settings[key] is None:
                settings[key] = default_val
            
        set_frame = ttk.LabelFrame(scrollable_frame, text=get_text("task_settings_title"), padding="10")
        set_frame.pack(fill=tk.X, expand=False, padx=10, pady=5)
        set_frame.columnconfigure(1, weight=1)
        
        # Định nghĩa loại và khóa cho mỗi mục cài đặt
        # type: entry, int_entry, bool, combo
        s_items = [
            ("output_dir_label", "output_dir", "dir_entry"),
            ("dpi_label", "dpi", "int_entry"),
            ("ratio_label", "ratio", "float_entry"),
            ("inpaint_label", "inpaint", "bool"),
            ("inpaint_method_label", "inpaint_method", "combo_method"),
            ("image_only_label", "image_only", "bool"),
            ("force_regenerate_label", "force_regenerate", "bool"),
            ("unify_font_label", "unify_font", "bool"),
            ("font_name_label", "font_name", "entry"),
            ("page_range_label", "page_range", "entry"),
        ]
        
        # Lưu các widget có thể cần ẩn
        unify_font_widgets = []
        font_name_widgets = []
        
        for i, (lbl_key, set_key, widget_type) in enumerate(s_items):
            # Thêm chiều rộng cho label để đảm bảo căn chỉnh
            lbl = ttk.Label(set_frame, text=get_text(lbl_key), font=("", 9, "bold"), width=20)
            lbl.grid(row=i, column=0, sticky="nw", pady=5)
            
            curr_val = settings.get(set_key)
            widget = None
            
            if widget_type == "bool":
                var = tk.BooleanVar(value=bool(curr_val))
                edit_vars[set_key] = var
                # Checkbutton khó nhìn khi bị disable; nếu ở trạng thái khoá, dùng Label hiển thị 'Có/Không'
                if not is_editable:
                    val_text = get_text("yes") if var.get() else get_text("no")
                    widget = ttk.Label(set_frame, text=val_text)
                    widget.grid(row=i, column=1, sticky="w", padx=10)
                else:
                    widget = ttk.Checkbutton(set_frame, variable=var)
                    widget.grid(row=i, column=1, sticky="w", padx=10)
                
            elif widget_type == "combo_method":
                # Xử lý hiển thị tên phương pháp, nếu là ID thì chuyển thành tên đã dịch
                if curr_val is not None:
                    # Nếu là method_id (ví dụ 'background_smooth'), chuyển thành tên đã dịch
                    if curr_val in ["background_smooth", "edge_mean_smooth", "background", "onion", "griddata", "skimage"]:
                        display_val = self.get_translated_name_from_id(curr_val)
                    else:
                        display_val = str(curr_val)
                else:
                    display_val = ""
                var = tk.StringVar(value=display_val)
                edit_vars[set_key] = var
                if not is_editable:
                    # Trạng thái khoá hiển thị bằng Label chỉ đọc để đảm bảo chữ rõ ràng
                    widget = ttk.Label(set_frame, text=display_val)
                    widget.grid(row=i, column=1, sticky="w", padx=10)
                else:
                    widget = ttk.Combobox(set_frame, textvariable=var, values=self.get_translated_method_names(), state="readonly")
                    widget.grid(row=i, column=1, sticky="ew", padx=10)
                
            elif widget_type == "dir_entry":
                var = tk.StringVar(value=str(curr_val) if curr_val is not None else "")
                edit_vars[set_key] = var
                if not is_editable:
                    # Ở trạng thái không thể chỉnh sửa, hiển thị bằng Label
                    widget = ttk.Label(set_frame, text=var.get())
                    widget.grid(row=i, column=1, sticky="w", padx=10)
                else:
                    widget = ttk.Frame(set_frame)
                    widget.grid(row=i, column=1, sticky="ew", padx=10)
                    ttk.Entry(widget, textvariable=var, state=entry_state).pack(side=tk.LEFT, fill=tk.X, expand=True)
                    def browse_dir(v=var):
                        d = filedialog.askdirectory(parent=top)
                        if d: v.set(d)
                    ttk.Button(widget, text=get_text("browse_btn"), command=browse_dir).pack(side=tk.RIGHT, padx=5)
                
            else: # entry, int_entry, float_entry
                var = tk.StringVar(value=str(curr_val) if curr_val is not None else "")
                edit_vars[set_key] = var
                if not is_editable:
                    # Ở trạng thái không thể chỉnh sửa, hiển thị bằng Label
                    widget = ttk.Label(set_frame, text=var.get())
                    widget.grid(row=i, column=1, sticky="w", padx=10)
                else:
                    widget = ttk.Entry(set_frame, textvariable=var)
                    widget.grid(row=i, column=1, sticky="ew", padx=10)

            if set_key == "unify_font":
                unify_font_widgets = [lbl, widget, i]
            elif set_key == "font_name":
                font_name_widgets = [lbl, widget, i]

        def update_details_unify_font_visibility(*args):
            is_visible = bool(json_var.get().strip())
            if is_visible:
                unify_font_widgets[0].grid(row=unify_font_widgets[2], column=0, sticky="nw", pady=5)
                unify_font_widgets[1].grid(row=unify_font_widgets[2], column=1, sticky="w", padx=10)
                
                font_name_widgets[0].grid(row=font_name_widgets[2], column=0, sticky="nw", pady=5)
                font_name_widgets[1].grid(row=font_name_widgets[2], column=1, sticky="ew", padx=10)
            else:
                unify_font_widgets[0].grid_forget()
                unify_font_widgets[1].grid_forget()
                font_name_widgets[0].grid_forget()
                font_name_widgets[1].grid_forget()

        json_var.trace_add("write", update_details_unify_font_visibility)
        update_details_unify_font_visibility()

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Các nút ở đáy
        btn_frame = ttk.Frame(top, padding="10")
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        def save_changes():
            # Cập nhật task["settings"]
            new_settings = {}
            for k, v in edit_vars.items():
                val = v.get()
                # Xử lý chuyển đổi kiểu
                # Lưu ý: để đơn giản, phần lớn lưu dưới dạng nguyên thủy; khi đọc, `run_conversion_for_task` sẽ xử lý lại
                # Nhưng để giữ nhất quán, cố gắng khôi phục kiểu
                orig_type_item = next((x for x in s_items if x[1] == k), None)
                if orig_type_item:
                    w_type = orig_type_item[2]
                    if w_type == "int_entry":
                        try:
                            new_settings[k] = int(val)
                        except:
                            new_settings[k] = val # fallback
                    elif w_type == "float_entry":
                        try:
                            new_settings[k] = float(val)
                        except:
                            new_settings[k] = val
                    elif w_type == "bool":
                        new_settings[k] = bool(val)
                    else:
                        new_settings[k] = val
                else:
                    new_settings[k] = val
            
            task["settings"] = new_settings
            # Cập nhật đường dẫn JSON
            task["json"] = json_var.get().strip().strip('"')
            # Cập nhật hiển thị Treeview
            self.update_task_row(task)
            
            print(f"Task {task['id']} updated.")
            top.destroy()

        ttk.Button(btn_frame, text=get_text("close_btn"), command=top.destroy).pack(side=tk.RIGHT, padx=5)
        # Chỉ task chưa bắt đầu mới được phép sửa cài đặt
        if is_editable:
            ttk.Button(btn_frame, text=get_text("save_btn"), command=save_changes).pack(side=tk.RIGHT, padx=5)

    def update_task_row(self, task):
        self.queue_tree.item(str(task["id"]), values=(
            task["id"], 
            self._get_display_path(task["pdf"]), 
            self._get_display_path(task["json"]), 
            task["status"], 
            self._get_display_path(task["output"])
        ))

    def start_queue(self):
        if self.is_queue_running:
            return

        if not self.task_queue:
            messagebox.showinfo(get_text("info_btn"), get_text("queue_empty_msg"))
            return

        # Kiểm tra xem có task cần tự động hoá (không phải chỉ chế độ ảnh)
        has_automation_task = any(not task.get("settings", {}).get("image_only", False) for task in self.task_queue)
        if has_automation_task:
            if not self.ensure_pc_manager_running():
                return
        if not self.task_queue:
            messagebox.showinfo(get_text("info_btn"), get_text("queue_empty_msg"))
            return
        self.queue_stop_flag = False
        self.is_queue_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        threading.Thread(target=self.process_queue, daemon=True).start()

    def stop_queue(self):
        if not self.is_queue_running:
            return
        self.queue_stop_flag = True
        print(get_text("queue_stopping"))
        self.stop_btn.config(state=tk.DISABLED)

    def process_queue(self):
        try:
            print(get_text("queue_started"))
            for task in list(self.task_queue):
                if self.queue_stop_flag:
                    break
                if not os.path.exists(task["pdf"]):
                    task["status"] = get_text("queue_status_error")
                    self.update_task_row(task)
                    continue
                task["status"] = get_text("queue_status_running")
                self.update_task_row(task)
                ok, output_files = self.run_conversion_for_task(task)
                if ok and output_files:
                    # output_files is a tuple: (unoptimized_file, optimized_file)
                    task["output_unoptimized"] = output_files[0] or ""
                    task["output_optimized"] = output_files[1] or ""
                    task["output"] = output_files[1] or output_files[0] or ""
                else:
                    task["output_unoptimized"] = ""
                    task["output_optimized"] = ""
                    task["output"] = ""
                task["status"] = get_text("queue_status_done") if ok else get_text("queue_status_error")
                self.update_task_row(task)
            if self.queue_stop_flag:
                print(get_text("queue_stopped"))
            else:
                print(get_text("queue_finished"))
        finally:
            self.is_queue_running = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    def run_conversion_for_task(self, task):
        try:
            pdf_file = task["pdf"]
            mineru_json = task["json"]
            settings = task.get("settings", {})
            
            # Lấy tham số từ cài đặt task, nếu thiếu thì dùng giá trị mặc định
            output_dir = settings.get("output_dir", self.output_dir_var.get() if hasattr(self, 'output_dir_var') else "workspace")
            dpi = settings.get("dpi", 150)
            ratio_val = settings.get("ratio", 0.8)
            inpaint = settings.get("inpaint", True)
            inpaint_method = settings.get("inpaint_method", self.get_translated_method_names()[0] if hasattr(self, 'get_translated_method_names') else "background_smooth")
            image_only = settings.get("image_only", False)
            force_regenerate = settings.get("force_regenerate", False)
            unify_font = settings.get("unify_font", True)
            font_name = settings.get("font_name", "Calibri")
            page_range = settings.get("page_range", "")
            
            # Cài đặt toàn cục (không lưu theo task, luôn dùng giá trị hiện tại trên giao diện)
            delay = self.delay_var.get() if hasattr(self, 'delay_var') else 0
            timeout = self.timeout_var.get() if hasattr(self, 'timeout_var') else 50
            done_offset_str = self.done_offset_var.get().strip() if hasattr(self, 'done_offset_var') else ""
            calibrate = self.calibrate_var.get() if hasattr(self, 'calibrate_var') else True

            pdf_name = Path(pdf_file).stem
            workspace_dir = Path(output_dir)
            png_dir = workspace_dir / f"{pdf_name}_pngs"
            ppt_dir = workspace_dir / f"{pdf_name}_ppt"
            tmp_image_dir = workspace_dir / "tmp_images"
            workspace_dir.mkdir(exist_ok=True, parents=True)
            
            done_offset = None
            if done_offset_str:
                try:
                    done_offset = int(done_offset_str)
                except ValueError:
                    pass

            ratio = min(screen_width/16, screen_height/9)
            max_display_width = int(16 * ratio)
            max_display_height = int(9 * ratio)
            display_width = int(max_display_width * ratio_val)
            display_height = int(max_display_height * ratio_val)
            
            def parse_page_range(range_str):
                if not range_str:
                    return None
                pages = set()
                range_str = range_str.replace('，', ',')
                range_str = range_str.replace('—', '-').replace('–', '-').replace('－', '-')
                for part in [p.strip() for p in range_str.split(',') if p.strip()]:
                    if '-' in part:
                        start_end = part.split('-')
                        if start_end[0] == '':
                            continue
                        start = int(start_end[0])
                        if start_end[1] == '':
                            pages.update(range(start, start + 10000))
                        else:
                            end = int(start_end[1])
                            if end >= start:
                                pages.update(range(start, end + 1))
                    else:
                        pages.add(int(part))
                return sorted(pages)
                
            def format_page_suffix(pages):
                if not pages:
                    return ""
                result = []
                i = 0
                while i < len(pages):
                    start = pages[i]
                    end = start
                    while i + 1 < len(pages) and pages[i + 1] == end + 1:
                        i += 1
                        end = pages[i]
                    if start == end:
                        result.append(str(start))
                    else:
                        result.append(f"{start}-{end}")
                    i += 1
                return f"_p{','.join(result)}"
            
            pages_list = None
            try:
                pages_list = parse_page_range(page_range)
            except Exception:
                pages_list = None
                
            page_suffix = format_page_suffix(pages_list)
            out_ppt_file = workspace_dir / f"{pdf_name}{page_suffix}.pptx"
            
            # Nếu inpaint_method đã là ID, dùng trực tiếp; nếu không, chuyển sang ID
            if inpaint_method in ["background_smooth", "edge_mean_smooth", "background", "onion", "griddata", "skimage"]:
                method_id = inpaint_method
            else:
                method_id = self.get_method_id_from_translated_name(inpaint_method)
            
            if image_only:
                png_names = pdf_to_png(
                    pdf_path=pdf_file,
                    output_dir=png_dir,
                    dpi=dpi,
                    inpaint=inpaint,
                    pages=pages_list,
                    inpaint_method=method_id,
                    force_regenerate=force_regenerate
                )
                if self.queue_stop_flag:
                    return False, None
                png_names = create_ppt_from_images(png_dir, out_ppt_file, png_names=png_names)
            else:
                png_names = process_pdf_to_ppt(
                    pdf_path=pdf_file,
                    png_dir=png_dir,
                    ppt_dir=ppt_dir,
                    delay_between_images=delay,
                    inpaint=inpaint,
                    dpi=dpi,
                    timeout=timeout,
                    display_height=display_height,
                    display_width=display_width,
                    done_button_offset=done_offset,
                    capture_done_offset=calibrate,
                    pages=pages_list,
                    update_offset_callback=self.update_offset_disk,
                    stop_flag=lambda: self.queue_stop_flag,
                    force_regenerate=force_regenerate,
                    inpaint_method=method_id,
                    top_left=self.top_left
                )
                if self.queue_stop_flag:
                    return False, None
                png_names = combine_ppt(ppt_dir, out_ppt_file, png_names=png_names)
                
            out_ppt_file = os.path.abspath(out_ppt_file)
            unoptimized_file = out_ppt_file
            optimized_file = None
            
            if not image_only and mineru_json:
                if os.path.exists(mineru_json):
                    refined_out = workspace_dir / f"{pdf_name}{page_suffix}_optimized.pptx"
                    refine_ppt(str(tmp_image_dir), mineru_json, str(out_ppt_file), str(png_dir), png_names, str(refined_out), unify_font=unify_font)
                    optimized_file = os.path.abspath(refined_out)
            
            print(get_text("queue_task_done", file=out_ppt_file))
            return True, (unoptimized_file, optimized_file)
        except Exception as e:
            print(get_text("conversion_fail", error=str(e)))
            return False, None

def launch_gui():
    # Enable Windows DPI awareness before creating the Tk root where possible
    try:
        enable_windows_dpi_awareness(None)
    except Exception:
        pass

    root = tk.Tk()
    # Thiết lập biểu tượng cửa sổ (an toàn: thử nhiều cách và bỏ qua nếu không thành công)
    try:
        ico = icon_path()
        if ico and os.path.exists(ico):
            try:
                root.iconbitmap(ico)
            except Exception:
                try:
                    root.iconbitmap(default=ico)
                except Exception:
                    pass
    except Exception:
        pass
    # After root exists, apply scaling using the helper (this will call tk scaling)
    try:
        enable_windows_dpi_awareness(root)
    except Exception:
        pass

    app = AppGUI(root)
    root.mainloop()

if __name__ == "__main__":
    launch_gui()
