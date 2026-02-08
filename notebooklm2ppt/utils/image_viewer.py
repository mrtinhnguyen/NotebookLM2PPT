# -*- coding: utf-8 -*-
# Sử dụng PIL + Tkinter để mở hình ảnh, co giãn theo tỷ lệ màn hình và hiển thị toàn màn hình; không có viền/thanh công cụ.

import os
import sys
import time
import ctypes
import tkinter
from PIL import Image, ImageTk


def _get_screen_resolution():
    # Windows lấy độ phân giải màn hình và bật nhận thức DPI để tránh ảnh hưởng của tỷ lệ
    try:
        user32 = ctypes.windll.user32
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return 1920, 1080


def show_image_fullscreen(image_path: str, display_height: int = None, stop_event=None, ready_event=None, stop_callback=None,top_left=(0,0)):
    """
    Hiển thị hình ảnh trên góc trên cùng bên trái của màn hình

    Args:
        image_path: Đường dẫn hình ảnh
        display_height: Chỉ định chiều cao hiển thị (đo lường pixel), nếu không có thì tự động thích ứng
        stop_event: đối tượng threading.Event, khi được đặt, cửa sổ sẽ đóng
        ready_event: đối tượng threading.Event, khi cửa sổ sẵn sàng, hãy đặt sự kiện này
        stop_callback: đối tượng có thể gọi, khi nhấn phím ESC, hàm callback này sẽ được gọi để dừng toàn bộ quá trình chuyển đổi
        top_left: Tọa độ góc trên cùng bên trái nơi hiển thị hình ảnh, mặc định (0,0)
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Không tìm thấy hình ảnh: {image_path}")

    # Sử dụng PIL để mở hình ảnh
    img = Image.open(image_path).convert("RGB")

    screen_w, screen_h = _get_screen_resolution()
    img_w, img_h = img.size

    # Tính tỷ lệ theo chiều cao được chỉ định hoặc kích thước màn hình
    if display_height is not None:
        scale = display_height / img_h
    else:
        scale = min(screen_w / img_w, screen_h / img_h)

    new_w = max(1, int(img_w * scale))
    new_h = max(1, int(img_h * scale))

    # Sử dụng PIL để điều chỉnh kích thước hình ảnh
    if scale != 1.0:
        # LANCZOS là bộ lọc lấy mẫu lại chất lượng cao
        img = img.resize((new_w, new_h), Image.LANCZOS)

    # Tạo hình ảnh lớn hơn một chút và thực hiện đệm cạnh (Edge Padding)
    # Thêm đệm trong bốn hướng, đảm bảo không có đường viền đen ở vùng top_left và bên phải/dưới
    if top_left[0] > 0 or top_left[1] > 0 or new_w < screen_w or new_h < screen_h:
        # Mục tiêu là lấp đầy toàn bộ màn hình
        target_w, target_h = screen_w, screen_h

        final_img = Image.new("RGB", (target_w, target_h))
        # Đặt hình ảnh vào vị trí được tính toán
        final_img.paste(img, (top_left[0], top_left[1]))

        # Lấp đầy bên trái
        if top_left[0] > 0:
            left_edge = img.crop((0, 0, 1, new_h))
            left_pad = left_edge.resize((top_left[0], new_h), Image.NEAREST)
            final_img.paste(left_pad, (0, top_left[1]))

        # Lấp đầy bên phải
        if top_left[0] + new_w < target_w:
            right_edge = img.crop((new_w - 1, 0, new_w, new_h))
            right_pad = right_edge.resize((target_w - (top_left[0] + new_w), new_h), Image.NEAREST)
            final_img.paste(right_pad, (top_left[0] + new_w, top_left[1]))

        # Lấp đầy phía trên (sử dụng các hàng đã lấp đầy trái-phải để kéo dãn)
        if top_left[1] > 0:
            top_line = final_img.crop((0, top_left[1], target_w, top_left[1] + 1))
            top_pad = top_line.resize((target_w, top_left[1]), Image.NEAREST)
            final_img.paste(top_pad, (0, 0))

        # Lấp đầy phía dưới
        if top_left[1] + new_h < target_h:
            bottom_line = final_img.crop((0, top_left[1] + new_h - 1, target_w, top_left[1] + new_h))
            bottom_pad = bottom_line.resize((target_w, target_h - (top_left[1] + new_h)), Image.NEAREST)
            final_img.paste(bottom_pad, (0, top_left[1] + new_h))

        img = final_img
        # Vì đã xử lý hình ảnh thành ảnh toàn màn hình chứa độ lệch, sau đó tọa độ vẽ được đặt thành (0,0)
        draw_x, draw_y = 0, 0
    else:
        draw_x, draw_y = top_left[0], top_left[1]

    # Kiểm tra xem đã có Tkinter root hay chưa, nếu có thì sử dụng Toplevel, nếu không thì tạo Tk mới
    is_toplevel = False
    try:
        # Cố gắng lấy root mặc định
        default_root = tkinter._default_root
        if default_root and default_root.winfo_exists():
            # Root đã tồn tại, sử dụng Toplevel
            root = tkinter.Toplevel()
            is_toplevel = True
        else:
            # Không có root hoặc root đã bị hủy, tạo Tk mới
            root = tkinter.Tk()
            is_toplevel = False
    except (AttributeError, tkinter.TclError):
        # Nếu có lỗi, tạo Tk mới
        root = tkinter.Tk()
        is_toplevel = False

    # Đặt không viền toàn màn hình
    root.overrideredirect(1)
    root.geometry("%dx%d+0+0" % (screen_w, screen_h))
    root.focus_set()

    # Tạo canvas và lấp đầy nền với màu đen
    # Loại bỏ tất cả các viền
    canvas = tkinter.Canvas(root, width=screen_w, height=screen_h, highlightthickness=0, borderwidth=0)
    canvas.pack()
    canvas.configure(background='black')

    # Chuyển đổi ảnh PIL thành đối tượng ảnh Tkinter
    # Phải giữ tham chiếu đến ảnh, nếu không nó sẽ bị thu gom rác
    tk_image = ImageTk.PhotoImage(img)

    # Hiển thị ảnh ở góc trên cùng bên trái của canvas (không căn giữa)
    # Điểm neo ảnh được đặt ở góc trên cùng bên trái (nw=northwest), tọa độ là (draw_x, draw_y)
    imagesprite = canvas.create_image(draw_x, draw_y, anchor='nw', image=tk_image)

    # Giữ tham chiếu đến ảnh để tránh bị thu gom rác
    canvas.image = tk_image

    # Thêm phản ứng phím ESC: nhấn ESC để dừng chuyển đổi và đóng cửa sổ
    def on_escape(event):
        print("\n⚠ Phát hiện phím ESC, đang dừng chuyển đổi...")
        # Kích hoạt callback dừng (dừng toàn bộ quá trình chuyển đổi)
        if stop_callback is not None:
            try:
                stop_callback()
            except Exception as e:
                print(f"Gọi callback dừng thất bại: {e}")
        # Kích hoạt sự kiện dừng
        if stop_event is not None:
            stop_event.set()
        # Đóng cửa sổ
        try:
            if not is_toplevel:
                root.quit()
            root.destroy()
        except:
            pass

    # Liên kết phím ESC
    root.bind('<Escape>', on_escape)

    # Đặt cửa sổ lên trên (Windows)
    try:
        root.attributes('-topmost', True)
        root.lift()
        root.focus_force()
    except Exception:
        pass

    # Buộc cập nhật cửa sổ để đảm bảo hiển thị
    root.update_idletasks()
    root.update()

    # Thông báo cửa sổ đã sẵn sàng
    if ready_event is not None:
        def signal_ready():
            # Chờ một chút để đảm bảo cửa sổ được render hoàn toàn
            ready_event.set()
        # Trì hoãn 500ms để thông báo sẵn sàng, đảm bảo cửa sổ đã hiển thị hoàn toàn
        root.after(500, signal_ready)

    # Nếu cung cấp stop_event, kiểm tra định kỳ xem có cần đóng cửa sổ không
    if stop_event is not None:
        def check_stop_event():
            if stop_event.is_set():
                try:
                    # Cửa sổ Toplevel chỉ cần destroy, không thể gọi quit()
                    # quit() sẽ thoát toàn bộ vòng lặp sự kiện Tkinter, làm cho GUI chính cũng thoát
                    if not is_toplevel:
                        root.quit()
                    root.destroy()
                except:
                    pass
            else:
                # Kiểm tra mỗi 50ms
                try:
                    root.after(50, check_stop_event)
                except:
                    pass

        # Bắt đầu kiểm tra
        try:
            root.after(50, check_stop_event)
        except:
            pass

    # Bắt đầu mainloop
    # Lưu ý: Cửa sổ Toplevel không cần gọi mainloop, vì vòng lặp sự kiện chính đã chạy
    # Ở chế độ Toplevel, thread sẽ giữ hoạt động cho đến khi cửa sổ được destroy
    if not is_toplevel:
        try:
            root.mainloop()
        except:
            pass
    else:
        # Chế độ Toplevel: không chặn, để vòng lặp sự kiện chính xử lý cửa sổ
        # Thread sẽ chờ ở đây cho đến khi cửa sổ được destroy
        try:
            # Sử dụng một vòng lặp đơn giản để giữ thread hoạt động
            while root.winfo_exists():
                time.sleep(0.1)
        except:
            pass


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "hinh_anh_trang_1.png"
    # Nếu cung cấp tham số thứ hai, hãy sử dụng nó làm chiều cao hiển thị
    height = int(sys.argv[2]) if len(sys.argv) > 2 else None
    show_image_fullscreen(path, display_height=height)
