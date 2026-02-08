"""Giao diện dòng lệnh: Chuyển đổi PDF thành bài thuyết trình PowerPoint có thể chỉnh sửa"""

import os
import time
import threading
import shutil
import argparse
import sys
from pathlib import Path
from .pdf2png import pdf_to_png
from .utils.image_viewer import show_image_fullscreen
from .utils.screenshot_automation import take_fullscreen_snip, screen_height, screen_width
from .utils.coordinate_utils import get_effective_top_left
from .utils.image_inpainter import INPAINT_METHODS
from .i18n import get_text


def process_pdf_to_ppt(pdf_path, png_dir, ppt_dir, delay_between_images=2, inpaint=True, dpi=150, timeout=50, display_height=None, 
                    display_width=None, done_button_offset=None, capture_done_offset: bool = True, pages=None, update_offset_callback=None, stop_flag=None, force_regenerate=False, inpaint_method='background_smooth', top_left=(0, 0)):
    """
    Chuyển đổi PDF thành hình ảnh PNG, sau đó xử lý chụp ảnh từng hình
    
    Args:
        pdf_path: Đường dẫn tệp PDF
        png_dir: Thư mục đầu ra PNG
        ppt_dir: Thư mục đầu ra PPT
        delay_between_images: Thời gian trễ giữa các hình ảnh (giây)
        inpaint: Có thực hiện sửa chữa hình ảnh hay không
        dpi: Độ rõ hình ảnh
        timeout: Thời gian chờ (giây)
        display_height: Chiều cao cửa sổ hiển thị
        display_width: Chiều rộng cửa sổ hiển thị
        done_button_offset: Độ lệch nút hoàn tất ở bên phải
        capture_done_offset: Có chụp được độ lệch nút hoàn tất hay không
        pages: Phạm vi số trang cần xử lý
        update_offset_callback: Hàm callback cập nhật độ lệch
        stop_flag: Cờ dừng (để ngắt chuyển đổi)
        force_regenerate: Có buộc tái tạo tất cả PPT hay không (mặc định False, sử dụng lại PPT hiện có)
        inpaint_method: Phương pháp sửa chữa, các giá trị tùy chọn: background_smooth, edge_mean_smooth, background, onion, griddata, skimage
        top_left: Tọa độ góc trên cùng bên trái của vùng chụp (x, y)
    """
    # 1. Chuyển đổi PDF thành hình ảnh PNG
    print("=" * 60)
    print("Bước 1: Chuyển đổi PDF thành hình ảnh PNG")
    print("=" * 60)
    
    if not os.path.exists(pdf_path):
        print(f"Lỗi: Tệp PDF {pdf_path} không tồn tại")
        return
    
    png_names = pdf_to_png(pdf_path, png_dir, dpi=dpi, inpaint=inpaint, pages=pages, inpaint_method=inpaint_method, force_regenerate=force_regenerate)
    
    # Tạo thư mục đầu ra ppt
    ppt_dir.mkdir(exist_ok=True, parents=True)
    print(f"Thư mục đầu ra PPT: {ppt_dir}")
    
    # Lấy đường dẫn thư mục tải xuống của người dùng
    downloads_folder = Path.home() / "Downloads"
    print(f"Thư mục tải xuống: {downloads_folder}")
    
    # 2. Lấy tất cả các tệp hình ảnh PNG và sắp xếp
    png_files = [png_dir / name for name in png_names]
    
    if not png_files:
        print(f"Lỗi: Không tìm thấy hình ảnh PNG trong {png_dir}")
        return
    
    print("\n" + "=" * 60)
    print(f"Bước 2: Xử lý {len(png_files)} hình ảnh PNG")
    print("=" * 60)
    
    # Đặt kích thước cửa sổ hiển thị (nếu không được chỉ định, hãy sử dụng kích thước màn hình)
    if display_height is None:
        display_height = screen_height
    if display_width is None:
        display_width = screen_width
    
    # Tính trước tọa độ top_left có hiệu lực thực tế, đảm bảo tất cả các thành phần tiếp theo sử dụng tọa độ hoàn toàn giống nhau
    effective_top_left = get_effective_top_left(top_left, display_width, display_height)
    print(f"Kích thước cửa sổ hiển thị: {display_width} x {display_height}, độ lệch thực: {effective_top_left}")

    # Tạo cờ dừng cục bộ để phản hồi phím ESC
    esc_stop_requested = [False]  # Sử dụng danh sách để sửa đổi trong chức năng lồng nhau

    # Tạo hàm cờ dừng kết hợp, đồng thời kiểm tra stop_flag lớp ngoài và yêu cầu dừng phím ESC
    def combined_stop_flag():
        return (stop_flag and stop_flag()) or esc_stop_requested[0]
    
    # 3. Xử lý chụp ảnh cho từng hình ảnh
    for idx, png_file in enumerate(png_files, 1):
        if combined_stop_flag():
            print("\n⏹️ Người dùng yêu cầu dừng chuyển đổi")
            break

        # Kiểm tra xem phím ESC có được nhấn hay không
        if esc_stop_requested[0]:
            print("\n⏹️ Người dùng nhấn phím ESC để dừng chuyển đổi")
            break
        
        print(f"\n[{idx}/{len(png_files)}] Xử lý hình ảnh: {png_file.name}")
        
        target_filename = png_file.stem + ".pptx"
        target_path = ppt_dir / target_filename
        
        if not force_regenerate and target_path.exists():
            print(f"  ✓ Tệp PPT đã tồn tại, bỏ qua chuyển đổi: {target_path}")
            continue
        
        stop_event = threading.Event()
        ready_event = threading.Event()

        # Tạo hàm callback để dừng toàn bộ quá trình chuyển đổi khi nhấn phím ESC
        def on_stop_requested():
            """Khi người dùng nhấn phím ESC, đặt cờ dừng"""
            print("Người dùng yêu cầu dừng chuyển đổi (nhấn phím ESC)")
            esc_stop_requested[0] = True

        def _viewer():
            """Hiển thị hình ảnh trong luồng"""
            # Truyền stop_event, ready_event và stop_callback
            show_image_fullscreen(str(png_file), display_height=display_height,
                                stop_event=stop_event, ready_event=ready_event,
                                stop_callback=on_stop_requested, top_left=effective_top_left)

        # Khởi động luồng hiển thị hình ảnh
        viewer_thread = threading.Thread(
            target=_viewer,
            name=f"tkinter_viewer_{idx}",
            daemon=True
        )
        viewer_thread.start()

        # Chờ cửa sổ sẵn sàng (tối đa 10 giây)
        print("Chờ cửa sổ hình ảnh hiển thị...")
        window_ready = ready_event.wait(timeout=10)
        if not window_ready:
            print("⚠ Hết thời gian hiển thị cửa sổ, tiếp tục...")
        else:
            print("✓ Cửa sổ hình ảnh đã được hiển thị")
            # Chờ thêm một chút thời gian để đảm bảo cửa sổ ổn định
            time.sleep(0.5)
        
        try:
            # Thực hiện chụp ảnh toàn màn hình và phát hiện cửa sổ PPT
            # Đối với trang đầu tiên, cho phép người dùng nhấp chuột thủ công và chụp độ lệch nút hoàn tất (nếu không được lưu hoặc bị yêu cầu buộc)
            capture_offset = (idx == 1 and capture_done_offset)
            if capture_offset:
                done_button_offset = None  # Buộc tái chụp độ lệch
            else:
                assert done_button_offset is not None, "Phải cung cấp độ lệch nút hoàn tất"
            success, ppt_filename, computed_offset = take_fullscreen_snip(
                check_ppt_window=True,
                ppt_check_timeout=timeout,
                width=display_width,
                height=display_height,
                done_button_right_offset=done_button_offset,
                stop_flag=combined_stop_flag,
                calibration_title=get_text("calibration_dialog_title"),
                calibration_msg=get_text("calibration_dialog_msg"),
                top_left=effective_top_left
            )
            if combined_stop_flag():
                print("\n⏹️ Người dùng yêu cầu dừng chuyển đổi")
                break
            if esc_stop_requested[0]:
                print("\n⏹️ Người dùng nhấn phím ESC để dừng chuyển đổi")
                break
            if success and computed_offset is not None:
                print(f"Độ lệch nút hoàn tất được chụp: {computed_offset}")
                done_button_offset = computed_offset  # Cập nhật thành độ lệch được chụp mới nhất
                if update_offset_callback:
                    update_offset_callback(computed_offset)


            if success and ppt_filename:
                print(f"✓ Hình ảnh {png_file.name} xử lý hoàn tát, cửa sổ PPT đã được tạo: {ppt_filename}")
                
                # Nếu trả về đường dẫn đầy đủ, hãy sử dụng trực tiếp
                if os.path.isabs(ppt_filename):
                    ppt_source_path = Path(ppt_filename)
                else:
                    # Tìm và sao chép tệp PPT từ thư mục tải xuống
                    if " - PowerPoint" in ppt_filename:
                        base_filename = ppt_filename.replace(" - PowerPoint", "").strip()
                    else:
                        base_filename = ppt_filename.strip()
                    
                    if not base_filename.endswith(".pptx"):
                        search_filename = base_filename + ".pptx"
                    else:
                        search_filename = base_filename
                    
                    ppt_source_path = downloads_folder / search_filename
                
                if not ppt_source_path.exists():
                    print(f"  Không tìm thấy {ppt_source_path}, cố gắng tìm tệp .pptx gần đây nhất...")
                    pptx_files = list(downloads_folder.glob("*.pptx"))
                    if pptx_files:
                        pptx_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                        ppt_source_path = pptx_files[0]
                        print(f"  Tìm thấy tệp PPT gần đây nhất: {ppt_source_path.name}")
                
                if ppt_source_path.exists():
                    shutil.copy2(ppt_source_path, target_path)
                    print(f"  ✓ Tệp PPT đã được sao chép: {target_path}")
                    
                    try:
                        ppt_source_path.unlink()
                        print(f"  ✓ Đã xóa tệp gốc: {ppt_source_path}")
                    except Exception as e:
                        print(f"  ⚠ Xóa tệp gốc thất bại: {e}")
                else:
                    print(f"  ⚠ Không tìm thấy tệp PPT trong thư mục tải xuống")
            elif success:
                print(f"✓ Hình ảnh {png_file.name} xử lý hoàn tát, nhưng không nhận được tên tệp PPT")
            else:
                print(f"⚠ Hình ảnh {png_file.name} đã được chụp, nhưng không phát hiện cửa sổ PPT mới")
                # Sử dụng effective_top_left được tính trước để định vị nút đóng
                from pywinauto import mouse
                close_button = (effective_top_left[0] + display_width - 35, effective_top_left[1] + display_height + 35)
                mouse.click(button='left', coords=close_button)
        except Exception as e:
            print(f"✗ Lỗi khi xử lý hình ảnh {png_file.name}: {e}")
        finally:
            stop_event.set()
            viewer_thread.join(timeout=2)
        
        if idx < len(png_files):
            print(f"Chờ {delay_between_images} giây trước khi xử lý tệp tiếp theo...")
            time.sleep(delay_between_images)
    
    print("\n" + "=" * 60)
    print(f"Hoàn tất! Đã xử lý tổng cộng {len(png_files)} hình ảnh")
    print("=" * 60)
    return png_names


def main():
    # Nếu không có tham số hoặc tham số đầu tiên là --gui, hãy khởi động GUI
    if len(sys.argv) == 1 or (len(sys.argv) > 1 and sys.argv[1] == "--gui"):
        from .gui import launch_gui
        launch_gui()
        return

    # Xóa CLI
    print("Chế độ dòng lệnh đã bị loại bỏ, vui lòng sử dụng giao diện GUI.")
    

if __name__ == "__main__":
    main()
