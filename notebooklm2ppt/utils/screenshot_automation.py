"""Tự động hóa tính năng Smart Select của Microsoft PC Manager.
    Args:
        initial_explorer_windows: danh sách cửa sổ File Explorer ban đầu [(hwnd, title), ...]
        timeout: thời gian chờ (giây), mặc định 10
        check_interval: khoảng thời gian kiểm tra (giây), mặc định 0.5
        stop_flag: hàm cờ dừng; trả về True để hủy
        target_folder_path: đường dẫn thư mục mục tiêu (từ đường dẫn PPT) để so khớp chính xác

    Returns:
        int: số cửa sổ đã đóng
"""

import re
import time
import threading
import win32api
import win32gui
import win32con
import win32com.client
import os
# Không nhập pywinauto ở cấp mô-đun, tránh xung đột với GUI chính, cũng như https://github.com/elliottzheng/NotebookLM2PPT/issues/8
# from pywinauto import mouse, keyboard
from pathlib import Path
from tkinter import messagebox
import tkinter as tk
# Get screen dimensions
screen_width = win32api.GetSystemMetrics(0)
screen_height = win32api.GetSystemMetrics(1)


def _wait_for_left_click(timeout: float = 60.0, stop_flag=None):
    """Chờ người dùng thực hiện một lần nhấp chuột bên trái, trả về tọa độ màn hình (x, y) khi nhấp. Hết thời gian trả về None.
    
    Args:
        timeout: Thời gian chờ (giây)
        stop_flag: Hàm cờ dừng, trả về True khi ngắt đợi
    """
    print(f'Vui lòng nhấp "Nút Hoàn tất" theo cách thủ công để lưu trang đầu tiên (Chờ {int(timeout)} giây)...')
    start = time.time()
    prev_state = bool(win32api.GetAsyncKeyState(0x01) & 0x8000)
    while time.time() - start < timeout:
        if stop_flag and stop_flag():
            print("Phát hiện yêu cầu dừng, ngắt đợi")
            return None
        state = bool(win32api.GetAsyncKeyState(0x01) & 0x8000)
        # Phát hiện lúc nhấn
        if state and not prev_state:
            # Ghi lại tọa độ khi nhấn
            x, y = win32api.GetCursorPos()
            # Chờ phát hành
            while bool(win32api.GetAsyncKeyState(0x01) & 0x8000):
                time.sleep(0.01)
            print(f"Phát hiện nhấp chuột bên trái tọa độ: {x}, {y}")
            return x, y
        prev_state = state
        time.sleep(0.01)
    print("Hết thời gian chờ người dùng nhấp chuột.")
    return None


def get_ppt_windows():
    """Lấy danh sách handle của tất cả các cửa sổ PowerPoint hiện có."""
    ppt_windows = []
    
    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            # Tên cửa sổ PowerPoint thường là "PPTFrameClass"
            # Cửa sổ WPS Presentation có thể chứa "WPS Presentation" hoặc trực tiếp hiển thị tên tệp
            if ("PPTFrameClass" in class_name or
                "PowerPoint" in window_text or
                "WPS" in window_text):
                results.append(hwnd)
        return True
    
    win32gui.EnumWindows(enum_callback, ppt_windows)
    return ppt_windows


def get_all_open_ppt_info():
    """Trả về dict map tên trình chiếu -> đường dẫn đầy đủ của tất cả các PPT đang mở.

    Cố gắng sử dụng COM cho PowerPoint và WPS (prog_id: PowerPoint.Application, Kwpp.Application).
    """
    info = {}
    for prog_id in ("PowerPoint.Application", "Kwpp.Application"):
        try:
            app = win32com.client.Dispatch(prog_id)
        except Exception:
            continue

        try:
            presentations = getattr(app, 'Presentations', None)
            if presentations is None:
                continue

            for pres in presentations:
                try:
                    name = getattr(pres, 'Name', None)
                    full = getattr(pres, 'FullName', None)
                    if name:
                        info[name] = full
                except Exception:
                    continue
        except Exception:
            continue

    return info


def get_all_open_ppt_paths():
    """Nhận danh sách đường dẫn tất cả các tệp PPT đang mở (bảo trì khả năng tương thích ngược)"""
    info = get_all_open_ppt_info()
    return list(info.values())


def get_explorer_windows():
    """Lấy danh sách các handle đến tất cả các cửa sổ File Explorer hiện tại"""
    explorer_windows = []
    
    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            # Tên cửa sổ trình quản lý tệp thường là "CabinetWClass"
            if "CabinetWClass" in class_name:
                results.append((hwnd, window_text))
        return True
    
    win32gui.EnumWindows(enum_callback, explorer_windows)
    return explorer_windows


def get_explorer_paths():
    """Lấy danh sách các đường dẫn thực tế trong tất cả các cửa sổ File Explorer."""
    try:
        # Sử dụng win32com thay vì comtypes sẽ ổn định hơn.
        shell = win32com.client.Dispatch("Shell.Application")
        windows = shell.Windows()
        
        paths = []
        for window in windows:
            try:
                location_url = window.LocationURL
                if location_url.startswith('file:///'):
                    path = location_url[8:].replace('/', '\\')
                    paths.append(path)
                elif location_url.startswith('::'):
                    shell_folder = window.Document.Folder
                    path = shell_folder.Self.Path
                    paths.append(path)
            except Exception as e:
                continue
        
        return paths
    except Exception as e:
        print(f"Nhận lỗi đường dẫn trình quản lý tệp: {e}")
        return []


def get_explorer_windows_with_paths():
    """Lấy danh sách tên người dùng, tiêu đề và đường dẫn cho tất cả các cửa sổ File Explorer hiện tại."""
    explorer_windows = get_explorer_windows()
    
    try:
        # Sử dụng win32com thay vì comtypes sẽ ổn định hơn.
        shell = win32com.client.Dispatch("Shell.Application")
        windows = shell.Windows()
        
        result = []
        # Cửa sổ để duyệt qua các phần tử liệt kê
        for hwnd, title in explorer_windows:
            # Hãy thử khớp với cửa sổ Shell tương ứng.
            for window in windows:
                try:
                    # Lấy tay nắm cửa sổ
                    window_hwnd = window.HWND
                    if window_hwnd == hwnd:
                        # Tìm đường dẫn thực tế
                        location_url = window.LocationURL
                        if location_url.startswith('file:///'):
                            path = location_url[8:].replace('/', '\\')
                        elif location_url.startswith('::'):
                            shell_folder = window.Document.Folder
                            path = shell_folder.Self.Path
                        else:
                            path = None
                        result.append((hwnd, title, path))
                        break
                except Exception as e:
                    continue
            else:
                # Nếu không tìm thấy kết quả phù hợp, hãy thêm None vào đường dẫn.
                result.append((hwnd, title, None))
        
        return result
    except Exception as e:
        print(f"Không thể truy xuất đường dẫn cửa sổ File Explorer.: {e}")
        return [(hwnd, title, None) for hwnd, title in explorer_windows]


def check_new_ppt_window(initial_windows, timeout=30, check_interval=1, stop_flag=None):
    """
    Kiểm tra xem cửa sổ PowerPoint mới có xuất hiện hay không
    
    Args:
        initial_windows: Danh sách các handle cửa sổ PowerPoint ban đầu
        timeout: Thời gian chờ (giây), mặc định 30 giây
        check_interval: Khoảng thời gian kiểm tra (giây), mặc định 1 giây
        stop_flag: Hàm cờ dừng; trả về True để ngắt quá trình chờ
    
    Returns:
        (bool, list, str): (Có tìm thấy cửa sổ mới hay không, danh sách các handle cửa sổ mới, tên tệp PowerPoint)
    """
    print(f"\nBắt đầu theo dõi các cửa sổ PowerPoint mới (thời gian chờ: {timeout} giây)...")
    start_time = time.time()
    detected_new_window = False
    last_loading_window = None  # Cửa sổ "mở" cuối cùng
    seen_windows = set(initial_windows)  # Theo dõi tất cả các cửa sổ đã được nhìn thấy
    
    while time.time() - start_time < timeout:
        if stop_flag and stop_flag():
            print("Phát hiện yêu cầu dừng, hủy kiểm tra cửa sổ PPT")
            return False, [], None
        
        current_windows = get_ppt_windows()
        new_windows = [w for w in current_windows if w not in seen_windows]
        
        # Cập nhật danh sách các cửa sổ đã thấy
        seen_windows.update(new_windows)
        
        if new_windows or detected_new_window:
            if new_windows and not detected_new_window:
                elapsed = time.time() - start_time
                print(f"✓ Phát hiện {len(new_windows)} cửa sổ PowerPoint mới (tốn: {elapsed:.1f}s)")
                detected_new_window = True
            
            # Hãy kiểm tra tất cả các cửa sổ hiện có (không chỉ các cửa sổ mới), vì tiêu đề cửa sổ có thể đã được cập nhật.
            all_new_windows = [w for w in current_windows if w not in initial_windows]
            
            for hwnd in all_new_windows:
                try:
                    window_text = win32gui.GetWindowText(hwnd)
                except:
                    continue
                
                # Kiểm tra xem nó có đang ở trạng thái tải tạm thời hay không.
                is_loading = window_text and ("Open" in window_text or "Opening" in window_text)
                
                if is_loading:
                    if hwnd != last_loading_window:
                        last_loading_window = hwnd
                        print(f"  - Phát hiện cửa sổ đang tải: {window_text}，đợi tải xong...")
                    continue
                
                # Hãy tìm một tên tệp hợp lệ (không rỗng và không ở trạng thái đang tải).
                # Không bao gồm các trường hợp chỉ có từ "PowerPoint" mà không có tên tệp.
                if window_text and window_text.strip():
                    # Nếu tiêu đề cửa sổ chỉ hiển thị "PowerPoint", điều đó có nghĩa là tệp tin chưa được tải; vui lòng tiếp tục chờ.
                    if window_text.strip().lower() == "powerpoint":
                        if hwnd != last_loading_window:
                            last_loading_window = hwnd
                            print(f"  - Tiêu đề cửa sổ chưa đầy đủ (chỉ hiển thị 'PowerPoint'), tiếp tục đợi...")
                        continue

                    print(f"  ✓ Cửa sổ đã tải xong: {window_text}")

                    return True, all_new_windows, window_text
        
        remaining = timeout - (time.time() - start_time)
        if remaining > 0:
            if detected_new_window:
                print(f"  Đang chờ tiêu đề cửa sổ cập nhật... (còn: {remaining:.0f}s)", end='\r')
            else:
                print(f"  Đang chờ... (còn: {remaining:.0f}s)", end='\r')
            time.sleep(check_interval)
    
    # Quá trình bị hết thời gian chờ, nhưng nếu phát hiện cửa sổ "đang mở", nó sẽ trả về thành công nhưng tên tệp là None.
    # Điều này cho phép người gọi thử tìm kiếm tệp tin mới nhất.
    if detected_new_window:
        print(f"\n⚠ Tiêu đề cửa sổ chưa cập nhật, sẽ cố gắng tìm file PPT gần đây")
        all_new_windows = [w for w in get_ppt_windows() if w not in initial_windows]
        return True, all_new_windows, None

    print(f"\n✗ Không phát hiện cửa sổ PowerPoint mới trong {timeout} giây")
    return False, [], None


def check_and_close_download_folder(initial_explorer_windows, timeout=10, check_interval=0.5, stop_flag=None, target_folder_path=None):
    """
    Kiểm tra xem cửa sổ File Explorer mới có xuất hiện không; đóng nó nếu có.
    
    Args:
        initial_explorer_windows: Danh sách ban đầu các cửa sổ File Explorer [(hwnd, title), ...]
        timeout: Thời gian chờ (giây), mặc định 10 giây
        check_interval: Khoảng thời gian kiểm tra (giây), mặc định 0,5 giây
        stop_flag: Hàm cờ dừng; trả về True để ngắt quá trình chờ
        target_folder_path: Đường dẫn thư mục đích (được trích xuất từ ​​đường dẫn PPT), được sử dụng để khớp chính xác
    
    Returns:
        int: Số lượng cửa sổ đã đóng
    """
    print(f"\nBắt đầu theo dõi cửa sổ File Explorer mới (timeout: {timeout}s)...")
    if target_folder_path:
        print(f"Thư mục mục tiêu: {target_folder_path}")
    start_time = time.time()
    closed_count = 0
    initial_hwnds = [hwnd for hwnd, _ in initial_explorer_windows]
    
    while time.time() - start_time < timeout:
        if stop_flag and stop_flag():
            print("Phát hiện yêu cầu dừng, hủy kiểm tra cửa sổ File Explorer")
            return closed_count
        
        # Dùng hàm mới để lấy thông tin cửa sổ, bao gồm đường dẫn
        current_windows = get_explorer_windows_with_paths()
        
        # Lấy các cửa sổ mới (chỉ dựa trên hwnd)
        new_windows = [(hwnd, title, path) for hwnd, title, path in current_windows if hwnd not in initial_hwnds]
        
        if new_windows:
            # Chỉ in thông tin khi phát hiện cửa sổ mới, giảm rườm rà
            # print(f"Cửa sổ File Explorer hiện tại: {len(current_windows)}")
            # for i, (hwnd, title, path) in enumerate(current_windows):
            #     print(f"    [{i+1}] hwnd={hwnd}, title='{title}', path={path}")
            
            print(f"  Phát hiện cửa sổ mới: {len(new_windows)}")
            for hwnd, title, path in new_windows:
                try:
                    should_close = False
                    
                    if target_folder_path:
                        # Chuẩn hóa đường dẫn để so sánh
                        normalized_target = os.path.normpath(target_folder_path)
                        
                        # Kiểm tra so khớp đường dẫn
                        if path:
                            normalized_path = os.path.normpath(path)
                            print(f"  So sánh đường dẫn: '{normalized_path}' vs '{normalized_target}'")
                            if normalized_path == normalized_target:
                                should_close = True
                                print(f"✓ Phát hiện cửa sổ File Explorer mới: {title}")
                                print(f"  → Đường dẫn trùng với thư mục mục tiêu, đang đóng...")
                    
                    if should_close:
                        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                        closed_count += 1
                        print(f"  → Đã gửi lệnh đóng")
                    
                    # Thêm cửa sổ đã xử lý vào danh sách ban đầu để tránh xử lý lại
                    initial_hwnds.append(hwnd)
                    
                except Exception as e:
                    print(f"  → Đóng cửa sổ thất bại: {e}")
            
            # Khi đã đóng cửa sổ, thoát vòng lặp kiểm tra
            if closed_count > 0:
                print(f"  → Đã đóng {closed_count} cửa sổ, thoát vòng kiểm tra")
                break
        
        remaining = timeout - (time.time() - start_time)
        if remaining > 0:
            time.sleep(check_interval)
    
    if closed_count > 0:
        print(f"\n✓ Đã đóng tổng cộng {closed_count} cửa sổ File Explorer")
    else:
        print(f"\n✓ Không phát hiện cửa sổ File Explorer cần đóng")
    
    return closed_count


def create_topmost_dialog(title, msg):    
    # Tạo một cửa sổ Tkinter đơn giản
    root = tk.Tk()
    root.withdraw()  # Ẩn cửa sổ chính
    # Đặt cửa sổ luôn ở trên cùng
    root.attributes("-topmost", True)   
    a = messagebox.askokcancel(title, msg, parent=root)
    root.destroy() 



def take_fullscreen_snip(
    delay_before_hotkey: float = 0.0,
    drag_duration: float = 3,
    click_duration: float = 0.1,
    check_ppt_window: bool = True,
    ppt_check_timeout: float = 30,
    width: int = screen_width,
    height: int = screen_height,
    done_button_right_offset: int | None = None,
    stop_flag=None,
    calibration_title: str = "Tip",
    calibration_msg: str = "Calibration in progress...",
    top_left: tuple[int, int] = (0, 0),
):
    """Sử dụng tính năng Smart Select của Microsoft PC Manager để chụp toàn màn hình.

    Args:
        delay_before_hotkey: thời gian chờ trước khi gửi Ctrl+Shift+A (giây)
        drag_duration: thời gian kéo để chọn (giây)
        click_duration: thời gian click nút hoàn tất (giây)
        check_ppt_window: có kiểm tra cửa sổ PPT mới hay không (mặc định True)
        ppt_check_timeout: timeout cho kiểm tra cửa sổ PPT (giây)
        width: chiều rộng ảnh chụp (mặc định màn hình)
        height: chiều cao ảnh chụp (mặc định màn hình)
        done_button_right_offset: offset phải của nút hoàn tất (px)
        stop_flag: hàm cờ dừng; trả về True để hủy
        calibration_title: tiêu đề hộp thoại hiệu chuẩn
        calibration_msg: nội dung hộp thoại hiệu chuẩn

    Returns:
        tuple: (bool, str|None, int|None) - (có tìm thấy cửa sổ mới, đường dẫn PPT hoặc tiêu đề, offset đã lưu hoặc None)
               Nếu không kiểm tra cửa sổ PPT, trả về (True, None, None)
    """

    # Trì hoãn import pywinauto để tránh xung đột với GUI chính khi module được nạp
    from pywinauto import mouse, keyboard

    # Ghi nhận các cửa sổ PPT và File Explorer trước khi thao tác
    initial_ppt_windows = get_ppt_windows() if check_ppt_window else []
    initial_ppt_paths = get_all_open_ppt_paths() if check_ppt_window else []
    initial_explorer_windows = get_explorer_windows()
    
    if check_ppt_window:
        print(f"Số cửa sổ PPT trước khi click: {len(initial_ppt_windows)}, số đường dẫn mở: {len(initial_ppt_paths)}")
    print(f"Số cửa sổ File Explorer trước khi click: {len(initial_explorer_windows)}")
    
    # In đường dẫn các cửa sổ File Explorer ban đầu (nếu có)
    initial_paths = get_explorer_paths()
    if initial_paths:
        print(f"Đường dẫn cửa sổ File Explorer trước khi click: {initial_paths}")

    if stop_flag and stop_flag():
        print("Phát hiện yêu cầu dừng, hủy thao tác chụp màn hình")
        return False, None, None

    time.sleep(delay_before_hotkey)

    if stop_flag and stop_flag():
        print("Phát hiện yêu cầu dừng, hủy thao tác chụp màn hình")
        return False, None, None


    # Đơn giản hoá logic: ưu tiên dùng tham số; nếu không có hoặc cần tái bắt thì yêu cầu click thủ công để lấy và lưu offset
    resolved_offset = None
    computed_offset = None
    if done_button_right_offset is not None:
        resolved_offset = int(done_button_right_offset)
        print(f"Sử dụng offset nút hoàn tất được truyền vào: {resolved_offset}")
    else:
        print("Không có offset nút hoàn tất truyền vào, sẽ yêu cầu click thủ công để lấy và lưu offset.")
        create_topmost_dialog(calibration_title, calibration_msg)

    if stop_flag and stop_flag():
        print("Phát hiện yêu cầu dừng, hủy thao tác chụp màn hình")
        return False, None, None

    keyboard.send_keys('^+a')
    time.sleep(2)

    if stop_flag and stop_flag():
        print("Phát hiện yêu cầu dừng, hủy thao tác chụp màn hình")
        return False, None, None

    # Define key points for the snip and confirmation click.
    # delta = 4  # Small offset to ensure full coverage
    delta = int(width / 512 * 4)
    # Tính toạ độ tuyệt đối
    abs_width = width + top_left[0]
    abs_height = height + top_left[1]

    bottom_right = (abs_width + delta, abs_height)

    print(f"Vùng chụp: {top_left} -> {bottom_right}, chiều rộng gốc: {width}")

    # Perform the drag operation
    # Move to start position
    mouse.move(coords=top_left)
    
    # Press left button
    mouse.press(button='left', coords=top_left)
    
    # Wait for the duration to simulate the drag time

    time.sleep(0)
    # Release left button
    mouse.release(button='left', coords=bottom_right)

    if stop_flag and stop_flag():
        print("Phát hiện yêu cầu dừng, hủy thao tác chụp màn hình")
        return False, None, None

    if resolved_offset is None:
        coords = _wait_for_left_click(timeout=60, stop_flag=stop_flag)
        if coords:
            click_x, click_y = coords
            computed_offset = int((bottom_right[0]) - click_x)
            print(f"Đã tính và lưu offset nút hoàn tất: {computed_offset}")
            resolved_offset = computed_offset
        else:
            print("Bắt offset lần đầu timeout hoặc không phát hiện click, hủy thao tác.")
            return False, None, None
    else:
        # Có offset, thực hiện click tự động
        done_button = (bottom_right[0] - resolved_offset, abs_height + 35)
        if done_button[1] > screen_height:
            done_button = (done_button[0], abs_height - 35)
        mouse.move(coords=done_button)
        time.sleep(0)
        mouse.click(button='left', coords=done_button)
    
    # Kiểm tra xem có cửa sổ PPT mới xuất hiện hay không
    if check_ppt_window:
        success, new_windows, ppt_filename = check_new_ppt_window(initial_ppt_windows, timeout=ppt_check_timeout, stop_flag=stop_flag)
        
        # Thử lấy đường dẫn đầy đủ thực tế của PPT
        actual_ppt_path = None
        if success:
            # Thêm logic thử lại, COM interface của PowerPoint đôi khi cập nhật chậm
            max_retries = 3
            for retry in range(max_retries):
                if retry > 0:
                    time.sleep(1)
                
                current_info = get_all_open_ppt_info()
                current_paths = list(current_info.values())
                
                # Chiến lược 1: tìm đường dẫn mới
                new_paths = [p for p in current_paths if p not in initial_ppt_paths]
                if new_paths:
                    actual_ppt_path = new_paths[0]
                    print(f"  ✓ Chiến lược 1 (so sánh đường dẫn) thành công: {actual_ppt_path}")
                    break
                
                # Chiến lược 2: khớp tên tệp qua tiêu đề cửa sổ
                if ppt_filename:
                    # Trích tên file cơ bản, ví dụ "SmartCopy_123.pptx - PowerPoint" -> "SmartCopy_123.pptx"
                    base_name = ppt_filename.replace(" - PowerPoint", "").strip()
                    if base_name in current_info:
                        actual_ppt_path = current_info[base_name]
                        print(f"  ✓ Chiến lược 2 (khớp tiêu đề) thành công: {actual_ppt_path}")
                        break
                    
                    # Thử khớp không có phần mở rộng
                    base_name_no_ext = base_name.rsplit('.', 1)[0]
                    for name, path in current_info.items():
                        if base_name_no_ext in name:
                            actual_ppt_path = path
                            print(f"  ✓ Chiến lược 2 (khớp mơ hồ) thành công: {actual_ppt_path}")
                            break
                    if actual_ppt_path:
                        break

            if not actual_ppt_path:
                # Nếu tất cả chiến lược thất bại, dùng tiêu đề cửa sổ làm fallback
                actual_ppt_path = ppt_filename
                print(f"  ⚠ Không tìm thấy đường dẫn mới trong danh sách Presentation, sẽ dùng tiêu đề cửa sổ: {ppt_filename}")

                # Sau khi có đường dẫn, đóng an toàn các cửa sổ PPT mới mở
            if new_windows:
                for hwnd in new_windows:
                    try:
                        title = win32gui.GetWindowText(hwnd)
                        if "smartcopy" in title.lower() or (ppt_filename and ppt_filename in title):
                            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                            print(f"  → Đã đóng cửa sổ PPT: {title}")
                    except:
                        continue
        
        # Lấy thư mục đích để đóng cửa sổ File Explorer tương ứng
        target_folder = None
        if actual_ppt_path and isinstance(actual_ppt_path, str) and len(actual_ppt_path) > 0:
            try:
                target_folder = str(Path(actual_ppt_path).parent)
            except:
                pass
        
        check_and_close_download_folder(initial_explorer_windows, timeout=10, stop_flag=stop_flag, target_folder_path=target_folder)
        
        return success, actual_ppt_path, computed_offset
    
    return True, None, None

if __name__ == "__main__":
    from .image_viewer import show_image_fullscreen

    image_path = "Hackathon_Architect_Playbook_pngs/page_0001.png"

    stop_event = threading.Event()
    ready_event = threading.Event()

    def _viewer():
        # Mở cửa sổ toàn màn hình (truyền stop_event và ready_event)
        show_image_fullscreen(image_path, stop_event=stop_event, ready_event=ready_event)

    t = threading.Thread(target=_viewer, name="tkinter_viewer", daemon=True)
    t.start()

    # Chờ cửa sổ sẵn sàng
    print("Đang chờ cửa sổ ảnh hiển thị...")
    if ready_event.wait(timeout=10):
        print("✓ Cửa sổ ảnh đã hiển thị")
        time.sleep(0.5)
    else:
        print("⚠ Hiển thị cửa sổ quá thời gian")

    try:
        take_fullscreen_snip()
    finally:
        # Thông báo đóng cửa sổ và chờ thread kết thúc
        stop_event.set()
        t.join(timeout=2)
