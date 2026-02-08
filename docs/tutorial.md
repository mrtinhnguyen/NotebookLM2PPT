---
title: Hướng dẫn sử dụng
---

# Hướng dẫn sử dụng

Hướng dẫn này sẽ giới thiệu chi tiết cách sử dụng công cụ NotebookLM2PPT, từ sử dụng cơ bản đến các tính năng nâng cao.

## Hướng dẫn sử dụng cơ bản

### Bước 1: Chuẩn bị

1. **Cài đặt Microsoft PC Manager**
   - Truy cập [trang web Microsoft PC Manager](https://pcmanager.microsoft.com/) để tải xuống và cài đặt
   - Đảm bảo phiên bản ≥ 3.17.50.0

2. **Cấu hình Smart Select**
   - Mở Microsoft PC Manager → Hộp công cụ → Smart Select
   - Đảm bảo phím tắt là `Ctrl + Shift + A`
   - Kiểm tra chức năng Smart Select, đảm bảo có thể thấy tùy chọn "Chuyển đổi sang PPT"

3. **Cài đặt NotebookLM2PPT**
   - Tải phiên bản biên dịch sẵn (khuyến nghị) hoặc cài đặt qua pip

### Bước 2: Chuyển đổi PDF

1. **Khởi động chương trình**
   - Nhấp đúp vào tệp thực thi hoặc chạy lệnh `notebooklm2ppt`

2. **Chọn tệp**
   - Nhấp nút "Duyệt" để chọn tệp PDF cần chuyển đổi
   - (Tùy chọn) Chọn tệp MinerU JSON để có kết quả tốt hơn

3. **Thiết lập tham số**
   - **DPI**: Điều khiển chất lượng hình ảnh, mặc định 200
   - **Tỷ lệ hiển thị**: Điều khiển kích thước hình ảnh, mặc định 0.8
   - **Độ trễ**: Điều khiển khoảng cách giữa các thao tác, mặc định 2 giây
   - **Thời gian chờ**: Điều khiển thời gian chờ đợi, mặc định 60 giây

4. **Bắt đầu chuyển đổi**
   - Nhấp nút "Bắt đầu chuyển đổi"
   - Chương trình sẽ tự động thực hiện quy trình chuyển đổi
   - Sau khi chuyển đổi hoàn tất, tệp PPT sẽ được tạo trong thư mục workspace

## Hướng dẫn tính năng nâng cao

### Sử dụng tối ưu hóa MinerU

1. **Lấy MinerU JSON**
   - Truy cập [trang web MinerU](https://mineru.net/)
   - Tải lên tệp PDF
   - Chờ phân tích hoàn tất
   - Tải xuống tệp JSON đã tạo

2. **Sử dụng tệp JSON**
   - Chọn tệp PDF trong chương trình
   - Chọn tệp JSON tương ứng
   - Nhấp "Bắt đầu chuyển đổi"
   - Chương trình sẽ thực hiện tối ưu hóa MinerU sau khi chuyển đổi cơ bản

### Sử dụng chế độ chỉ hình ảnh

1. **Khởi động chương trình**
2. Đánh dấu tùy chọn "Chế độ chỉ hình ảnh"
3. Chọn tệp PDF
4. Nhấp "Bắt đầu chuyển đổi"
5. Chương trình sẽ bỏ qua Smart Select, trực tiếp chèn hình ảnh vào PPT

### Lựa chọn phương pháp sửa chữa hình ảnh

1. **Khởi động chương trình**
2. Chọn phương pháp phù hợp trong menu thả xuống "Phương pháp sửa chữa hình ảnh"
3. Nhấp "Bắt đầu chuyển đổi"

**Phương pháp khuyến nghị**:
- **Làm mịn thông minh**: Hiệu quả tổng hợp tốt nhất, phù hợp với hầu hết các tình huống
- **Lấp đầy trung bình cạnh**: Phù hợp với nền đơn sắc
- **Lấp đầy đơn sắc siêu tốc**: Phù hợp với nền tối giản, tốc độ nhanh nhất

## Mẹo sử dụng

### 1. Nâng cao chất lượng chuyển đổi

- **Tăng DPI**: Đối với yêu cầu chất lượng cao, đặt DPI thành 300
- **Sử dụng tối ưu hóa MinerU**: Lấy hình ảnh gốc chất lượng cao
- **Chọn phương pháp sửa chữa phù hợp**: Chọn theo độ phức tạp của nền

### 2. Tăng tốc độ chuyển đổi

- **Giảm DPI**: Đối với chuyển đổi nhanh, đặt DPI thành 150
- **Sử dụng chế độ chỉ hình ảnh**: Bỏ qua Smart Select, nhanh hơn
- **Giảm tỷ lệ hiển thị**: Giảm thời gian hiển thị trên màn hình

### 3. Giải quyết vấn đề thường gặp

- **Hiệu chuẩn vị trí nút**: Bắt buộc hiệu chuẩn khi sử dụng lần đầu
- **Giữ tiêu điểm cửa sổ**: Trong quá trình chuyển đổi, không thao tác chuột bàn phím
- **Kiểm tra thư mục tải xuống**: Đảm bảo tệp tạm thời có thể lưu đúng

### 4. Xử lý hàng loạt

1. **Chuẩn bị nhiều tệp PDF**
2. **Chuyển đổi từng tệp**: Hiện tại không hỗ trợ chuyển đổi hàng loạt, cần xử lý từng tệp
3. **Thiết lập thống nhất**: Sử dụng cùng tham số để đảm bảo tính nhất quán

## Thực tiễn tốt nhất

### Tình huống 1: Bản trình chiếu NotebookLM

1. **Tạo PDF**: Tạo bản trình chiếu PDF trong NotebookLM
2. **Lấy JSON**: Tải lên MinerU để lấy tệp JSON
3. **Tối ưu hóa chuyển đổi**: Sử dụng tham số mặc định + tối ưu hóa MinerU
4. **Kiểm tra kết quả**: Đảm bảo hộp văn bản và hình ảnh chính xác

### Tình huống 2: Chuyển đổi nhanh

1. **Chọn tệp**: Chọn PDF cần chuyển đổi
2. **Sử dụng chế độ chỉ hình ảnh**: Bỏ qua Smart Select
3. **Hoàn thành nhanh**: Phù hợp với tình huống không yêu cầu cao về khả năng chỉnh sửa

### Tình huống 3: Chuyển đổi chất lượng cao

1. **Đặt DPI thành 300**: Nâng cao chất lượng hình ảnh
2. **Lấy MinerU JSON**: Đạt hiệu quả tối ưu hóa tốt nhất
3. **Chọn sửa chữa làm mịn thông minh**: Giữ chất lượng nền
4. **Kiên nhẫn chờ đợi**: Chuyển đổi chất lượng cao cần nhiều thời gian hơn

## Câu hỏi thường gặp

**Q: Chương trình không phản hồi trong quá trình chuyển đổi thì phải làm sao?**
A: Đây là hiện tượng bình thường, chương trình đang thực hiện thao tác tự động hóa. Vui lòng không đóng cưỡng bức, hãy chờ chuyển đổi hoàn tất.

**Q: Chất lượng hình ảnh trong PPT tạo ra không tốt thì phải làm sao?**
A: Tăng tham số DPI, hoặc sử dụng tối ưu hóa MinerU để lấy hình ảnh gốc chất lượng cao.

**Q: Smart Select không có tùy chọn "Chuyển đổi sang PPT" thì phải làm sao?**
A: Đảm bảo Microsoft PC Manager đã được cập nhật lên phiên bản mới nhất, kiểm tra xem đã bật chương trình trải nghiệm trước chưa.

**Q: Tệp MinerU JSON có bắt buộc không?**
A: Không bắt buộc. Nhưng sử dụng tệp JSON có thể đạt hiệu quả tối ưu hóa tốt hơn.

**Q: Tốc độ chuyển đổi quá chậm thì phải làm sao?**
A: Thử giảm DPI, sử dụng chế độ chỉ hình ảnh, đóng các ứng dụng khác.

Qua hướng dẫn này, bạn có thể thành thạo sử dụng công cụ NotebookLM2PPT để chuyển đổi PDF thành bản trình chiếu PowerPoint có thể chỉnh sửa chất lượng cao.
