import fitz  # PyMuPDF
import os
from pathlib import Path
from .utils.image_inpainter import inpaint_image, INPAINT_METHODS
from PIL import Image

def pdf_to_png(pdf_path, output_dir=None, dpi=150, inpaint=False, pages=None, inpaint_method='background_smooth', force_regenerate=False, make_wide_screen=False):
    """
    Chuyển đổi tệp PDF thành nhiều hình ảnh PNG
    
    Args:
        pdf_path: Đường dẫn tệp PDF
        output_dir: Thư mục đầu ra, mặc định là thư mục pdf_name_pngs ở cùng thư mục với PDF
        dpi: Độ phân giải, mặc định 150
        inpaint: Có thực hiện sửa chữa hình ảnh không
        pages: Phạm vi số trang cần xử lý
        inpaint_method: Phương pháp sửa chữa, giá trị tùy chọn: background_smooth, edge_mean_smooth, background, onion, griddata, skimage
        force_regenerate: Có buộc tạo lại tất cả PNG không (mặc định False, sử dụng lại PNG đã tồn tại)
        make_wide_screen: Có biến thành hình ảnh màn hình rộng không, thích ứng với trang PPT 16:9
    """
    # Mở tệp PDF
    pdf_doc = fitz.open(pdf_path)
    
    # Xác định thư mục đầu ra
    if output_dir is None:
        pdf_name = Path(pdf_path).stem  # Lấy tên tệp PDF (không có phần mở rộng)
        output_dir = Path(pdf_path).parent / f"{pdf_name}_pngs"
    else:
        output_dir = Path(output_dir)
    
    # Tạo thư mục đầu ra
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Hệ số chuyển đổi: DPI / 72 (DPI màn hình mặc định)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    
    # Duyệt qua từng trang
    page_count = len(pdf_doc)  # Lấy số trang trước khi đóng tài liệu
    # Chuẩn hóa tham số pages thành tập hợp, để tiện so sánh
    pages_set = None
    if pages is not None:
        pages_set = set(pages)

    png_names = []
    for page_num, page in enumerate(pdf_doc, 1):
        # Nếu chỉ định pages, hãy bỏ qua các trang không trong phạm vi
        if pages_set is not None and page_num not in pages_set:
            continue
        # Hiển thị trang dưới dạng hình ảnh
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Lưu thành PNG
        output_path = output_dir / f"page_{page_num:04d}.png"
        
        png_names.append(output_path.name)

        if not force_regenerate and os.path.exists(output_path):
            print(f"Bỏ qua tệp đã tồn tại: {output_path}")
            continue
        pix.save(output_path)
        print(f"✓ Đã lưu: {output_path}")
        if inpaint:
            inpaint_image(str(output_path), str(output_path), inpaint_method=inpaint_method)
            print(f"✓ Đã sửa chữa: {output_path}")

        if make_wide_screen:
            # Biến thành hình ảnh màn hình rộng 16:9
            img = Image.open(output_path)
            width, height = img.size
            target_width = round(height * 16 / 9)
            if target_width > width:
                # Cần mở rộng chiều rộng
                new_img = Image.new("RGB", (target_width, height), (255, 255, 255))
                new_img.paste(img, ((target_width - width) // 2, 0))
                new_img.save(output_path)
                print(f"✓ Đã điều chỉnh thành màn hình rộng: {output_path}")
            elif target_width < width:
                # Cần cắt chiều rộng
                left = (width - target_width) // 2
                right = left + target_width
                cropped_img = img.crop((left, 0, right, height))
                cropped_img.save(output_path)
                print(f"✓ Đã cắt thành màn hình rộng: {output_path}")
            else:
                print(f"✓ Đã là màn hình rộng, không cần điều chỉnh: {output_path}")

    pdf_doc.close()
    print(f"\nHoàn tất! Chuyển đổi {page_count} trang, thư mục đầu ra: {output_dir}")
    return png_names

def pngs2pdf(png_files, output_pdf):
    """
    Hợp nhất nhiều hình ảnh PNG thành một tệp PDF
    
    Tham số:
        png_files: Danh sách đường dẫn tệp PNG
        output_pdf: Đường dẫn tệp PDF đầu ra
    """
    if not png_files:
        print("Không có danh sách tệp PNG được cung cấp, không thể tạo PDF.")
        return

    image_list = []
    for png_file in png_files:
        img = Image.open(png_file).convert("RGB")
        image_list.append(img)

    # Lưu dưới dạng PDF
    first_image = image_list[0]
    rest_images = image_list[1:]
    first_image.save(output_pdf, save_all=True, append_images=rest_images)
    print(f"✓ Đã tạo PDF: {output_pdf}")

if __name__ == "__main__":
    # Ví dụ sử dụng
    pdf_file = r"examples\Floyd_Quy_hoach.pdf"  # Thay đổi thành đường dẫn tệp PDF của bạn
    
    if os.path.exists(pdf_file):
        out_dir = 'tmp_pngs'
        png_names = pdf_to_png(pdf_file, dpi=150, output_dir=out_dir, make_wide_screen=True)
        png_files = [os.path.join(out_dir, name) for name in png_names]
        output_pdf = "output_widescreen.pdf"
        pngs2pdf(png_files, output_pdf)
    else:
        print(f"Lỗi: Tệp {pdf_file} không tồn tại")
