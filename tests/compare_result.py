import os
import sys
from pathlib import Path
import win32com.client
import fitz  # PyMuPDF
from PIL import Image

# Đảm bảo có thể nhập các mô-đun trong dự án
sys.path.append(str(Path(__file__).parent.parent))
from notebooklm2ppt.pdf2png import pdf_to_png

def pptx_to_pdf(pptx_path, pdf_output_path):
    """
    Chuyển đổi tệp PPTX thành tệp PDF
    
    Args:
        pptx_path: Đường dẫn tệp PPTX
        pdf_output_path: Đường dẫn tệp PDF đầu ra
    """
    print(f"Đang chuyển đổi PPTX thành PDF: {pptx_path}")
    
    # Tạo đối tượng ứng dụng PowerPoint
    powerpoint = win32com.client.Dispatch("PowerPoint.Application")
    
    # Mở tệp PPTX
    presentation = powerpoint.Presentations.Open(pptx_path)
    
    # Lưu dưới dạng PDF
    presentation.SaveAs(pdf_output_path, 32)  # 32 = Định dạng PDF
    
    # Đóng bài thuyết trình
    presentation.Close()
    
    # Thoát PowerPoint
    powerpoint.Quit()
    
    print(f"✓ Đã lưu PDF: {pdf_output_path}")

def compare_pdf_and_pptx(pdf_path, pptx1_path, pptx2_path, output_dir=None, dpi=150):
    """
    So sánh tệp PDF và hai tệp PPTX được chuyển đổi từ nó
    
    Args:
        pdf_path: Đường dẫn tệp PDF nguồn
        pptx1_path: Đường dẫn tệp PPTX đầu tiên
        pptx2_path: Đường dẫn tệp PPTX thứ hai
        output_dir: Thư mục đầu ra, mặc định là thư mục compare_results ở cùng thư mục với PDF
        dpi: Độ rõ hình ảnh, mặc định 150
    """
    # Xác định thư mục đầu ra
    if output_dir is None:
        pdf_name = Path(pdf_path).stem
        output_dir = Path(pdf_path).parent / "compare_results"
    else:
        output_dir = Path(output_dir)
    
    # Tạo thư mục đầu ra
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Chuyển đổi PPTX thành PDF
    pptx1_pdf = output_dir / f"{Path(pptx1_path).stem}.pdf"
    pptx2_pdf = output_dir / f"{Path(pptx2_path).stem}.pdf"
    
    pptx_to_pdf(pptx1_path, str(pptx1_pdf))
    pptx_to_pdf(pptx2_path, str(pptx2_pdf))
    
    # Chuyển đổi PDF sang JPG (sử dụng cùng thư mục, phân biệt bằng hậu tố tên tệp)
    jpg_dir = output_dir / "jpgs"
    
    print("\nĐang chuyển đổi PDF nguồn sang JPG...")
    # Để phân biệt hình ảnh từ các nguồn khác nhau, chuyển đổi sang thư mục tạm trước, sau đó đổi tên sang thư mục thống nhất
    temp_pdf_dir = output_dir / "temp_pdf"
    pdf_jpgs = pdf_to_png(pdf_path, temp_pdf_dir, dpi=dpi, force_regenerate=True)
    
    print("\nĐang chuyển đổi PDF từ PPTX đầu tiên sang JPG...")
    temp_pptx1_dir = output_dir / "temp_pptx1"
    pptx1_jpgs = pdf_to_png(str(pptx1_pdf), temp_pptx1_dir, dpi=dpi, force_regenerate=True)
    
    print("\nĐang chuyển đổi PDF từ PPTX thứ hai sang JPG...")
    temp_pptx2_dir = output_dir / "temp_pptx2"
    pptx2_jpgs = pdf_to_png(str(pptx2_pdf), temp_pptx2_dir, dpi=dpi, force_regenerate=True)
    
    # Tạo thư mục JPG thống nhất
    jpg_dir.mkdir(exist_ok=True)
    
    # Đổi tên và di chuyển tất cả tệp JPG vào thư mục thống nhất
    print("\nĐang sắp xếp tệp JPG vào thư mục thống nhất...")
    
    # Xác định kích thước mục tiêu thống nhất (sử dụng kích thước hình ảnh PDF nguồn làm chuẩn)
    target_width = 0
    target_height = 0
    
    # Lấy kích thước hình ảnh PDF nguồn làm chuẩn
    for jpg_name in pdf_jpgs:
        src_path = temp_pdf_dir / jpg_name
        if src_path.exists():
            from PIL import Image
            img = Image.open(src_path)
            target_width = max(target_width, img.width)
            target_height = max(target_height, img.height)
    
    # Nếu không có hình ảnh PDF nguồn, sử dụng kích thước mặc định
    if target_width == 0 or target_height == 0:
        target_width = 800
        target_height = 600
    
    print(f"\nSử dụng kích thước thống nhất: {target_width} x {target_height}")
    
    # Di chuyển tệp JPG của PDF nguồn
    for jpg_name in pdf_jpgs:
        src_path = temp_pdf_dir / jpg_name
        # Sử dụng hậu tố số để đảm bảo hình ảnh chuyển đổi từ PDF nguồn được xếp trước: page_0001_0.jpg
        base_name = jpg_name.rsplit('.', 1)[0]
        # Bắt buộc sử dụng phần mở rộng jpg
        new_name = f"{base_name}_0_source.jpg"
        dst_path = jpg_dir / new_name
        if src_path.exists():
            # Chuyển đổi sang định dạng jpg và điều chỉnh kích thước trước
            from PIL import Image
            img = Image.open(src_path)
            # Điều chỉnh về kích thước thống nhất
            img = img.resize((target_width, target_height))
            img.save(dst_path, 'JPEG', quality=95)
            print(f"  ✓ Đã chuyển đổi và điều chỉnh kích thước: {dst_path.name}")
    
    # Di chuyển tệp JPG của PPTX đầu tiên
    for jpg_name in pptx1_jpgs:
        src_path = temp_pptx1_dir / jpg_name
        # Sử dụng hậu tố số: page_0001_1.jpg
        base_name = jpg_name.rsplit('.', 1)[0]
        # Bắt buộc sử dụng phần mở rộng jpg
        new_name = f"{base_name}_1_converted.jpg"
        dst_path = jpg_dir / new_name
        if src_path.exists():
            # Chuyển đổi sang định dạng jpg và điều chỉnh kích thước trước
            from PIL import Image
            img = Image.open(src_path)
            # Điều chỉnh về kích thước thống nhất
            img = img.resize((target_width, target_height))
            img.save(dst_path, 'JPEG', quality=95)
            print(f"  ✓ Đã chuyển đổi và điều chỉnh kích thước: {dst_path.name}")
    
    # Di chuyển tệp JPG của PPTX thứ hai
    for jpg_name in pptx2_jpgs:
        src_path = temp_pptx2_dir / jpg_name
        # Sử dụng hậu tố số: page_0001_2.jpg
        base_name = jpg_name.rsplit('.', 1)[0]
        # Bắt buộc sử dụng phần mở rộng jpg
        new_name = f"{base_name}_2_converted.jpg"
        dst_path = jpg_dir / new_name
        if src_path.exists():
            # Chuyển đổi sang định dạng jpg và điều chỉnh kích thước trước
            from PIL import Image
            img = Image.open(src_path)
            # Điều chỉnh về kích thước thống nhất
            img = img.resize((target_width, target_height))
            img.save(dst_path, 'JPEG', quality=95)
            print(f"  ✓ Đã chuyển đổi và điều chỉnh kích thước: {dst_path.name}")
    
    # Dọn dẹp thư mục tạm
    import shutil
    for temp_dir in [temp_pdf_dir, temp_pptx1_dir, temp_pptx2_dir]:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"  ✓ Đã dọn dẹp thư mục tạm: {temp_dir.name}")
    
    # Xác định số trang tối đa
    max_pages = max(len(pdf_jpgs), len(pptx1_jpgs), len(pptx2_jpgs))
    print(f"\nSố trang tối đa: {max_pages}")

    # Ghép nối hình ảnh theo chiều ngang
    print("\nĐang ghép nối hình ảnh theo chiều ngang...")
    combined_dir = output_dir / "combined"
    combined_dir.mkdir(exist_ok=True)
    
    for i in range(max_pages):
        page_num = i + 1
        print(f"  Đang xử lý trang {page_num}...")

        # Lấy đường dẫn tệp JPG của trang tương ứng (lấy tệp có hậu tố số từ thư mục thống nhất)
        pdf_jpg_path = jpg_dir / f"page_{page_num:04d}_0_source.jpg"
        pptx1_jpg_path = jpg_dir / f"page_{page_num:04d}_1_converted.jpg"
        pptx2_jpg_path = jpg_dir / f"page_{page_num:04d}_2_converted.jpg"
        
        # Tải hình ảnh
        images = []

        # Xác định kích thước hình ảnh thống nhất
        target_width = 0
        target_height = 0
        
        # Lấy kích thước tất cả hình ảnh trước, xác định kích thước lớn nhất
        img_paths = [pdf_jpg_path, pptx1_jpg_path, pptx2_jpg_path]
        for path in img_paths:
            if path.exists():
                img = Image.open(path)
                target_width = max(target_width, img.width)
                target_height = max(target_height, img.height)
        
        # Nếu không tìm thấy hình ảnh nào, sử dụng kích thước mặc định
        if target_width == 0 or target_height == 0:
            target_width = 800
            target_height = 600
        
        # Tải và điều chỉnh tất cả hình ảnh về kích thước thống nhất
        for path in img_paths:
            if path.exists():
                img = Image.open(path)
                # Điều chỉnh hình ảnh về kích thước thống nhất
                img = img.resize((target_width, target_height))
            else:
                # Tạo hình ảnh trắng
                img = Image.new('RGB', (target_width, target_height), color='white')
            images.append(img)
        
        # Tính toán kích thước hình ảnh sau khi ghép nối
        total_width = target_width * 3
        max_height = target_height
        
        # Tạo hình ảnh sau khi ghép nối
        combined = Image.new('RGB', (total_width, max_height), color='white')
        
        # Ghép nối hình ảnh
        x_offset = 0
        for img in images:
            combined.paste(img, (x_offset, 0))
            x_offset += target_width
        
        # Lưu ảnh sau khi ghép nối
        combined_path = combined_dir / f"combined_page_{page_num:04d}.jpg"
        combined.save(combined_path, 'JPEG', quality=95)
        print(f"  ✓ Đã lưu: {combined_path}")
    
    print(f"\n✅ So sánh hoàn thành!")
    print(f"nõ Thư mục đầu ra: {output_dir}")
    print(f"nõ Thư mục ảnh sau khi ghép: {combined_dir}")

def main():
    """
    Hàm chính
    """
    if len(sys.argv) != 4:
        print("Cách dùng: python compare_result.py <file pdf> <file pptx 1> <file pptx 2>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    pptx1_path = sys.argv[2]
    pptx2_path = sys.argv[3]
    
    # Kiểm tra xem các tệp có tồn tại không
    if not os.path.exists(pdf_path):
        print(f"Łỗi: Tệp PDF không tồn tại: {pdf_path}")
        sys.exit(1)
    
    if not os.path.exists(pptx1_path):
        print(f"Łỗi: Tệp PPTX 1 không tồn tại: {pptx1_path}")
        sys.exit(1)
    
    if not os.path.exists(pptx2_path):
        print(f"Łỗi: Tệp PPTX 2 không tồn tại: {pptx2_path}")
        sys.exit(1)
    
    # Thực hiện so sánh
    compare_pdf_and_pptx(pdf_path, pptx1_path, pptx2_path)

if __name__ == "__main__":
    main()
