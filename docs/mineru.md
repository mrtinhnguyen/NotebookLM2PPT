---
title: Tối ưu hóa MinerU
---

# Tối ưu hóa chuyên sâu MinerU

Tài liệu này mô tả chi tiết các chi tiết triển khai kỹ thuật của chức năng tối ưu hóa chuyên sâu MinerU trong NotebookLM2PPT, phù hợp cho nhân viên kỹ thuật tham khảo.

## Nguyên lý cốt lõi

Chức năng tối ưu hóa MinerU phân tích tệp JSON do MinerU tạo ra, trích xuất thông tin cấu trúc trang, thực hiện tối ưu hóa chuyên sâu trên PPT được tạo từ chuyển đổi cơ bản, nâng cao chất lượng bố cục, độ rõ nét hình ảnh và độ chính xác văn bản.

## Mô-đun cốt lõi

**Tệp**: `notebooklm2ppt/utils/ppt_refiner.py`

**Hàm chính**:

```python
def refine_ppt(tmp_image_dir, json_file, ppt_file, png_dir, png_files, final_out_ppt_file, unify_font=None, font_name=None)
```

**Mô tả tham số**:
- `tmp_image_dir`: Thư mục hình ảnh tạm thời
- `json_file`: Đường dẫn tệp JSON do MinerU tạo
- `ppt_file`: Đường dẫn tệp PPT từ chuyển đổi cơ bản
- `png_dir`: Thư mục hình ảnh PNG từ chuyển đổi PDF
- `png_files`: Danh sách tệp PNG
- `final_out_ppt_file`: Đường dẫn tệp PPT đã tối ưu hóa đầu ra cuối cùng
- `unify_font`: Có thống nhất phông chữ không (tùy chọn, mặc định theo cài đặt tệp cấu hình)
- `font_name`: Tên phông chữ thống nhất sử dụng (tùy chọn, mặc định là "Microsoft YaHei")

## Quy trình tối ưu hóa

### 1. Lọc hộp văn bản thông minh

**Vấn đề**: Chuyển đổi cơ bản có thể nhận diện ra các hộp văn bản không liên quan

**Giải pháp**: Sử dụng thuật toán IOU (Intersection over Union) để đánh giá mức độ trùng lặp giữa hộp văn bản và khối nội dung PDF

**Triển khai**:
```python
def compute_iou(boxA, boxB):
    # Tính diện tích giao nhau của hai hình chữ nhật
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interWidth = max(0, xB - xA)
    interHeight = max(0, yB - yA)
    interArea = interWidth * interHeight

    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou
```

**Logic lọc**:
- Tính IOU của mỗi hộp văn bản với khối nội dung PDF
- Giữ lại hộp văn bản có IOU > 0.01 (liên quan mạnh)
- Xóa hộp văn bản có IOU ≤ 0.01 (có thể là phần tử không liên quan)

### 2. Xử lý thống nhất phông chữ

**Vấn đề**: Trong PPT từ chuyển đổi cơ bản, phông chữ của các hộp văn bản có thể khác nhau

**Giải pháp**: Thống nhất phông chữ tất cả hộp văn bản thành "Microsoft YaHei"

**Triển khai**:
```python
# Tạo đối tượng phông chữ Microsoft YaHei
newFont = TextFont("Microsoft YaHei")

# Duyệt qua tất cả phạm vi văn bản trong hộp văn bản
for textRange in paragraph.TextRanges:
    textRange.LatinFont = newFont
```

### 3. Thay thế hình ảnh chất lượng cao

**Vấn đề**: Hình ảnh trong quá trình chuyển đổi cơ bản có thể bị nén hoặc giảm chất lượng

**Giải pháp**: Cắt vùng hình ảnh gốc từ PNG chất lượng cao được render từ PDF và thay thế

**Triển khai**:
```python
# Cắt và lưu hình ảnh tạm thời
image_crop = image_cv[top_bg:bottom_bg, left_bg:right_bg]
Image.fromarray(image_crop).save(tmp_image_path)

# Thay thế hình ảnh trong PPT
rect1 = RectangleF.FromLTRB(left, top + delta_y, right, bottom + delta_y)
image = slide.Shapes.AppendEmbedImageByPath(ShapeType.Rectangle, tmp_image_path, rect1)
image.Line.FillType = FillFormatType.none
image.ZOrderPosition = 0  # Đặt hình ảnh ở lớp dưới cùng
```

### 4. Xử lý nền thông minh

**Vấn đề**: Cần cân bằng giữa lấp đầy vùng đơn sắc và giữ lại nền phức tạp

**Giải pháp**: Phán đoán thông minh dựa trên tính nhất quán màu cạnh (đa dạng) và khả dụng của nền cũ

**Triển khai**:
```python
from notebooklm2ppt.utils.edge_diversity import compute_edge_diversity_numpy

diversity, fill_color = compute_edge_diversity_numpy(image_cv, left, top, right, bottom, tolerance=15)

if old_bg_cv is None or diversity < 0.5:
    # Màu cạnh tương đối nhất quán (gần đơn sắc) hoặc không có nền cũ, lấp đầy bằng màu chủ đạo
    image_cv[top:bottom, left:right] = fill_color
else:
    # Màu cạnh thay đổi nhiều (nền phức tạp), giữ lại nền gốc
    image_cv[top:bottom, left:right] = old_bg_cv[top:bottom, left:right]
```

Trong đó:
- `diversity` thuộc [0, 1], giá trị càng nhỏ thì màu cạnh càng gần đơn sắc
- `fill_color` là màu lấp đầy được tính từ màu chủ đạo của cạnh

## Quy trình làm việc hoàn chỉnh

### 1. Chuẩn bị dữ liệu

```python
# 1. Tải MinerU JSON
data = load_json(json_file)
pdf_info = data['pdf_info']

# 2. Lọc thông tin theo số trang
indices = get_indices_from_png_names(png_files)
pdf_info = [pdf_info[i] for i in indices]

# 3. Tính tỷ lệ thu phóng
pdf_w, _ = pdf_info[0]['page_size']
presentation = Presentation()
presentation.LoadFromFile(ppt_file)
ppt_H, ppt_W = presentation.SlideSize.Size.Height, presentation.SlideSize.Size.Width
ppt_scale = ppt_W / pdf_w
```

### 2. Xử lý từng trang

```python
for page_index, slide in enumerate(presentation.Slides):
    # 1. Lọc hộp văn bản thông minh và thống nhất phông chữ
    # 2. Thay thế hình ảnh chất lượng cao
    # 3. Xử lý nền thông minh
```

### 3. Lưu kết quả

```python
presentation.SaveToFile(final_out_ppt_file, FileFormat.Pptx2019)
print(f"Tối ưu hóa hoàn tất! Tệp đầu ra: {final_out_ppt_file}")

# Dọn dẹp PPT
clean_ppt(final_out_ppt_file, final_out_ppt_file)
```

## Thuật toán quan trọng

### Thuật toán IOU (Intersection over Union)

**Ứng dụng**: Lọc hộp văn bản
**Nguyên lý**: Tính mức độ trùng lặp của hai vùng hình chữ nhật
**Ngưỡng**: 0.01 (ngưỡng hợp lý đã được xác minh qua thực nghiệm)

### Thuật toán phát hiện đa dạng cạnh

**Ứng dụng**: Xử lý nền
**Nguyên lý**: Thống kê tỷ lệ màu chủ đạo của pixel cạnh bốn cạnh khối văn bản, tỷ lệ màu chủ đạo càng cao, đa dạng càng thấp
**Đầu ra**:
- `diversity = 1 - main_ratio`, `main_ratio` là tỷ lệ màu chủ đạo
- `fill_color` là màu RGB trung bình tương ứng với màu chủ đạo
**Ngưỡng**: 0.5 (khi `diversity < 0.5` được coi là vùng gần đơn sắc, có thể lấp đầy bằng màu chủ đạo)

## Tham số kỹ thuật

| Tham số | Giá trị mặc định | Tác dụng | Ảnh hưởng |
|---------|-------------------|----------|-----------|
| **Ngưỡng IOU** | 0.01 | Lọc hộp văn bản | Ảnh hưởng số lượng hộp văn bản được giữ lại |
| **Ngưỡng đa dạng cạnh** | 0.5 | Xử lý nền | Càng nhỏ càng dễ xác định là vùng đơn sắc |
| **Dung sai màu cạnh** | 15 | Lượng tử hóa màu cạnh | Dung sai càng lớn càng ít nhạy, màu chủ đạo ổn định hơn |
| **Bộ nhớ đệm hình ảnh** | Bật | Tối ưu hiệu suất | Giảm thao tác cắt lặp lại |

## Tối ưu hiệu suất

1. **Cắt cục bộ**: Cắt trực tiếp vùng hình ảnh từ hình render trang chất lượng cao, đảm bảo tính nhất quán cao giữa hình ảnh và nền.
2. **Xử lý theo trang**: Xử lý tuần tự theo đơn vị trang, logic rõ ràng, thuận tiện cho debug và mở rộng song song hóa.
3. **Quản lý bộ nhớ**: Sử dụng garbage collection Python giải phóng mảng tạm theo trang, tránh chiếm dụng bộ nhớ quá cao.

## Xử lý sự cố

### Vấn đề thường gặp

| Vấn đề | Nguyên nhân có thể | Giải pháp |
|--------|---------------------|-----------|
| **Vị trí cắt hình ảnh bị lệch** | Tính toán tỷ lệ thu phóng không chính xác hoặc bố cục PDF phức tạp | Kiểm tra logic tính toán `ppt_scale` và `image_scale` |
| **Lọc hộp văn bản không chính xác** | Ngưỡng IOU không phù hợp hoặc chất lượng phân tích JSON kém | Điều chỉnh ngưỡng IOU, kiểm tra chất lượng JSON |
| **Hiệu quả xử lý nền không tốt** | Cài đặt ngưỡng không phù hợp | Điều chỉnh ngưỡng đa dạng cạnh hoặc dung sai màu cạnh |
| **Tốc độ tối ưu chậm** | Tài liệu lớn hoặc độ phân giải hình ảnh trang cực cao | Giảm độ phân giải render PNG phù hợp |

### Gợi ý debug

1. **Bật chế độ debug**: Đặt biến môi trường `NOTEBOOKLM2PPT_DEBUG=1`
2. **Kiểm tra tệp JSON**: Xác nhận định dạng tệp JSON chính xác, chứa đầy đủ thông tin trang
3. **Điều chỉnh ngưỡng**: Điều chỉnh ngưỡng thuật toán (IOU, đa dạng, dung sai) theo tình hình thực tế

## Phụ thuộc kỹ thuật

- **Spire.Presentation**: Dùng cho thao tác và chỉnh sửa PPT
- **NumPy**: Dùng cho tính toán số, thao tác mảng hình ảnh và thống kê màu cạnh
- **Requests**: Dùng cho tải hình ảnh MinerU
- **Pillow**: Dùng cho đọc ghi và thu phóng hình ảnh (hình nền và ảnh chụp trang)

## Tài liệu liên quan

- [Nguyên lý hoạt động](implementation): Tìm hiểu quy trình làm việc tổng thể
- [Bắt đầu nhanh](quickstart): Tìm hiểu cách sử dụng tối ưu hóa MinerU
- [Giới thiệu tính năng](features): Tìm hiểu các tính năng cốt lõi của tối ưu hóa MinerU
