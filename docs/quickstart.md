---
title: Bắt đầu nhanh
---

# Bắt đầu nhanh

Tài liệu này sẽ hướng dẫn bạn cách nhanh chóng bắt đầu sử dụng công cụ NotebookLM2PPT để chuyển đổi PDF thành bản trình chiếu PowerPoint có thể chỉnh sửa chất lượng cao.

## Yêu cầu hệ thống

- **Hệ điều hành**: Windows 10/11
- **Microsoft PowerPoint hoặc WPS**: Dùng để mở và chỉnh sửa tệp PPT đã tạo
- **[Microsoft PC Manager](https://pcmanager.microsoft.com/)**: Phiên bản ≥ 3.17.50.0

## Cài đặt

### Khuyến nghị: Tải phiên bản biên dịch sẵn

1. Truy cập trang [Releases](https://github.com/elliottzheng/NotebookLM2PPT/releases)
2. Tải tệp thực thi `.exe` mới nhất
3. Nhấp đúp để chạy, không cần cài đặt môi trường Python

### Các cách cài đặt khác

**Cài đặt qua pip**:
```bash
pip install notebooklm2ppt -U
```

**Cài đặt từ mã nguồn**:
```bash
pip install git+https://github.com/elliottzheng/NotebookLM2PPT.git
```

## Cấu hình Microsoft PC Manager

1. Mở Microsoft PC Manager -> **Hộp công cụ**
2. Tìm **Smart Select**, đảm bảo đã bật
3. Xác nhận phím tắt là `Ctrl + Shift + A`
4. Kiểm tra: Nhấn phím tắt, đảm bảo có thể thấy giao diện chọn vùng và xuất hiện tùy chọn "Chuyển đổi sang PPT"

## Quy trình sử dụng cơ bản

### Bước 1: Khởi động chương trình

- Nhấp đúp vào tệp `.exe` đã tải, hoặc
- Chạy trong dòng lệnh: `notebooklm2ppt`

### Bước 2: Chọn tệp

- Nhấp nút "Duyệt" để chọn tệp PDF cần chuyển đổi
- (Tùy chọn) Chọn tệp MinerU JSON tương ứng để có kết quả chuyển đổi tốt hơn

### Bước 3: Thiết lập tham số

Đối với lần sử dụng đầu tiên, khuyến nghị sử dụng tham số mặc định:
- **DPI**: 200 (điều khiển chất lượng hình ảnh)
- **Tỷ lệ hiển thị**: 0.8 (điều khiển kích thước hình ảnh)
- **Độ trễ**: 2 giây (điều khiển khoảng cách giữa các thao tác)
- **Thời gian chờ**: 60 giây (điều khiển thời gian chờ đợi)

### Bước 4: Hiệu chuẩn vị trí nút (bắt buộc khi sử dụng lần đầu)

1. Đánh dấu tùy chọn "Hiệu chuẩn vị trí nút"
2. Chương trình sẽ hiển thị giao diện Smart Select
3. Nhấp thủ công vào nút "Chuyển đổi sang PPT"
4. Chương trình sẽ tự động lưu giá trị offset, lần sử dụng tiếp theo không cần hiệu chuẩn lại

### Bước 5: Bắt đầu chuyển đổi

1. Nhấp nút "Bắt đầu chuyển đổi"
2. Chương trình sẽ tự động thực hiện quy trình chuyển đổi
3. Trong quá trình chuyển đổi, vui lòng không thao tác chuột bàn phím
4. Sau khi chuyển đổi hoàn tất, tệp PPT sẽ được tạo trong thư mục `workspace`

## Tối ưu hóa với MinerU

### Bước 1: Lấy MinerU JSON

1. Truy cập [trang web MinerU](https://mineru.net/)
2. Tải lên tệp PDF của bạn
3. Chờ phân tích hoàn tất (thường mất vài phút)
4. Tải xuống tệp JSON đã tạo

### Bước 2: Sử dụng tệp JSON

1. Chọn tệp PDF trong chương trình
2. Chọn tệp JSON tương ứng
3. Nhấp nút "Bắt đầu chuyển đổi"
4. Chương trình sẽ thực hiện tối ưu hóa MinerU sau khi chuyển đổi cơ bản

## Chế độ chỉ hình ảnh

Để chuyển đổi nhanh, có thể sử dụng chế độ chỉ hình ảnh:

1. Đánh dấu tùy chọn "Chế độ chỉ hình ảnh"
2. Chọn tệp PDF cần chuyển đổi
3. Nhấp nút "Bắt đầu chuyển đổi"
4. Chương trình sẽ trực tiếp chèn hình ảnh vào PPT, nhanh hơn nhưng nội dung không thể chỉnh sửa

## Phương pháp sửa chữa hình ảnh

Trong chương trình, bạn có thể chọn các phương pháp sửa chữa hình ảnh khác nhau:

- **Làm mịn thông minh** (khuyến nghị): Hiệu quả tổng hợp tốt nhất, phù hợp với hầu hết các tình huống
- **Lấp đầy trung bình cạnh**: Phù hợp với nền đơn sắc
- **Lấp đầy đơn sắc siêu tốc**: Phù hợp với nền tối giản, tốc độ nhanh nhất
- **Sửa chữa co dần từng lớp**: Phù hợp sửa chữa vết xước hoặc đường kẻ mỏng dài
- **Nội suy chuyển tiếp gradient**: Phù hợp với nền có gradient
- **Sửa chữa ánh sáng song điều hòa**: Giữ tính liên tục của ánh sáng, tốc độ chậm hơn

## Lưu ý

- **Giữ tiêu điểm cửa sổ**: Trong quá trình chuyển đổi, vui lòng không thao tác chuột bàn phím
- **Kiểm tra thư mục tải xuống**: Đảm bảo tệp tạm thời có thể lưu đúng vào thư mục tải xuống của hệ thống
- **Cập nhật phần mềm**: Đảm bảo Microsoft PC Manager đã được cập nhật lên phiên bản mới nhất
- **Kết nối mạng**: Khi sử dụng tối ưu hóa MinerU cần kết nối mạng ổn định

## Câu hỏi thường gặp

**Q: Tệp MinerU JSON có bắt buộc không?**
A: Không bắt buộc. Khi không cung cấp tệp JSON, chương trình sẽ sử dụng chức năng chuyển đổi cơ bản.

**Q: MinerU có phải dịch vụ miễn phí không?**
A: Có, hiện tại MinerU là dịch vụ miễn phí, chỉ cần đăng ký để sử dụng.

**Q: Tốc độ chuyển đổi quá chậm thì phải làm sao?**
A: Có thể thử giảm tham số DPI, sử dụng chế độ chỉ hình ảnh hoặc đóng các ứng dụng chiếm tài nguyên khác.

**Q: Chất lượng hình ảnh trong PPT tạo ra không tốt thì phải làm sao?**
A: Có thể tăng tham số DPI (ví dụ đặt thành 300) hoặc sử dụng tối ưu hóa MinerU để lấy hình ảnh gốc chất lượng cao.

## Thực tiễn tốt nhất

1. **Sử dụng lần đầu**:
   - Đảm bảo Microsoft PC Manager đã được cập nhật lên phiên bản mới nhất
   - Hiệu chuẩn vị trí nút
   - Sử dụng tham số mặc định để kiểm tra

2. **Tối ưu tham số**:
   - Đối với tài liệu thông thường, sử dụng tham số mặc định là đủ
   - Đối với yêu cầu chất lượng cao, đặt DPI thành 300
   - Đối với tài liệu lớn, tăng thời gian trễ và thời gian chờ phù hợp

3. **Lựa chọn quy trình**:
   - Đối với tài liệu quan trọng, sử dụng tối ưu hóa MinerU
   - Đối với chuyển đổi nhanh, sử dụng chế độ chỉ hình ảnh
   - Đối với nền phức tạp, chọn phương pháp làm mịn thông minh

4. **Kiểm tra kết quả**:
   - Kiểm tra PPT đã tạo sau khi chuyển đổi hoàn tất
   - Xác nhận hộp văn bản, hình ảnh và nền có chính xác không
   - Điều chỉnh thủ công theo nhu cầu

Bằng cách tuân theo hướng dẫn trên, bạn có thể nhanh chóng làm quen với NotebookLM2PPT và chuyển đổi PDF thành bản trình chiếu PowerPoint có thể chỉnh sửa chất lượng cao.
