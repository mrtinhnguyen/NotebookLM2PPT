# 🚀 NotebookLM2PPT

> **Biến các bản trình chiếu do NotebookLM tạo thành công cụ thực sự phục vụ bạn**
> Công cụ chuyển đổi thông minh từ PDF sang PowerPoint có thể chỉnh sửa hoàn toàn


[Phiên bản mới nhất ![](https://img.shields.io/github/release/mrtinhnguyen/NotebookLM2PPT.svg)] | [Tài liệu](https://elliottzheng.github.io/NotebookLM2PPT) | [Tải về](https://github.com/elliottzheng/NotebookLM2PPT/releases)

---

## Giới thiệu dự án

**NotebookLM2PPT** là một công cụ tự động mạnh mẽ, giúp chuyển các tài liệu PDF không thể chỉnh sửa (đặc biệt là các slide do NotebookLM tạo) thành các bản PowerPoint có thể chỉnh sửa hoàn toàn.

### Giá trị chính
- **🤖 Tự động hoàn toàn**: Sử dụng tính năng "Smart Select" của Microsoft PC Manager để tự động chụp màn hình, nhận diện, chuyển đổi và ghép slide.
- **🧠 Tối ưu sâu bằng MinerU** (tuỳ chọn): Tích hợp khả năng phân tích của MinerU để tái bố cục văn bản, đồng nhất font và thay thế bằng ảnh chất lượng cao.
- **✨ Loại bỏ watermark thông minh**: Thuật toán tích hợp để xử lý watermark đặc thù từ NotebookLM.
- **📦 Xử lý hàng loạt** (v1.1.0): Hỗ trợ hàng đợi tác vụ, cho phép thêm nhiều PDF và JSON MinerU để xử lý tự động theo thứ tự。

---

## 🌟 Minh hoạ kết quả

Bên trái là chuyển đổi cơ bản (chụp màn hình + nhận dạng), bên phải là **sau khi tối ưu bằng MinerU** (tái bố cục + ảnh HD):

| **PPT chuyển đổi cơ bản** | **PPT được tối ưu hóa bằng MinerU** |
| :--- | :--- |
| ![Basic](docs/public/page_0004_1_converted.jpg) | ![MinerU](docs/public/page_0004_2_converted.jpg) |
| ![Basic](docs/public/page_0003_1_converted.jpg) | ![MinerU](docs/public/page_0003_2_converted.jpg) |

> 💡 **Ấn tượng với kết quả?** Xem [so sánh chi tiết](https://mrtinhnguyen.github.io/NotebookLM2PPT/compare.html) và [dữ liệu hiệu suất](https://mrtinhnguyen.github.io/NotebookLM2PPT/features.html)。

---

## 🚀 Bắt đầu nhanh

Xem hướng dẫn chi tiết tại [Hướng dẫn bắt đầu nhanh](https://mrtinhnguyen.github.io/NotebookLM2PPT/quickstart.html).

### 1. Yêu cầu hệ thống
- **Windows 10/11**
- **Microsoft PowerPoint** hoặc **WPS Office** (hỗ trợ từ v0.6.5+)
- **Microsoft PC Manager** ([tải ở đây](https://pcmanager.microsoft.com/)) (phiên bản $\ge$ 3.17.50.0 và bật tính năng "Smart Select")

### 2. Cài đặt
- **Khuyến nghị**: Tải tệp `.exe` từ trang [Releases](https://github.com/mrtinhnguyen/NotebookLM2PPT/releases) và chạy.
- **Dành cho nhà phát triển**: `pip install notebooklm2ppt -U`

### 3. Các bước sử dụng
1. **Khởi chạy ứng dụng**: chạy file exe hoặc gõ `notebooklm2ppt` trong dòng lệnh.
2. **Chọn tệp**: chọn PDF cần chuyển đổi.
3. **Hiệu chuẩn vị trí**: **lần đầu sử dụng hãy bật 'Calibrate button position'** và làm theo hướng dẫn để click nút "Convert to PPT" trên màn hình.
4. **Bắt đầu chuyển đổi**: chương trình sẽ tự điều khiển chuột để hoàn thành thao tác。

---

## 🧠 Tính năng nâng cao: Tối ưu hóa xử lý hậu kỳ MinerU

Muốn có bố cục chuyên nghiệp? Hãy sử dụng các tính năng tối ưu hóa của MinerU:

1. Tải tệp PDF của bạn lên [trang web MinerU](https://mineru.net/) và tải xuống tệp JSON đã được phân tích cú pháp.
2. Khi chọn tệp PDF trong công cụ này, hãy chọn cả tệp JSON tương ứng.
3. Sau khi quá trình chuyển đổi cơ bản hoàn tất, chương trình sẽ tự động thực hiện tối ưu hóa chuyên sâu (sắp xếp lại văn bản, thống nhất phông chữ và thay thế hình ảnh độ phân giải cao).

👉 [Tìm hiểu thêm về chi tiết tối ưu hóa của MinerU](https://mrtinhnguyen.github.io/NotebookLM2PPT/mineru.html)

---

## ⚠️ Câu hỏi thường gặp và lưu ý quan trọng

- **🔴 Điểm then chốt: Hiệu chuẩn độ lệch nút bấm**
  Công cụ này dựa vào mô phỏng nhấp chuột. Nếu không thể tự động nhấp nút "Chuyển đổi thành PPT", hãy chắc chắn chọn "Hiệu chuẩn vị trí nút" trên giao diện để hiệu chuẩn lại.
- **🚫 Vui lòng không can thiệp**
  Trong quá trình chuyển đổi, chương trình sẽ kiểm soát chuột, vui lòng không di chuyển chuột hoặc nhấn phím (nhấn `ESC` có thể dừng khẩn cấp).
- **📂 Không tìm thấy tệp?**
  Theo mặc định, chương trình sẽ trích xuất tệp tạm thời từ thư mục "Tải xuống" của hệ thống, vui lòng đảm bảo đường dẫn tải xuống không thay đổi.

---

## 📚 Hướng dẫn tài liệu

- [Bắt đầu nhanh](https://mrtinhnguyen.github.io/NotebookLM2PPT/quickstart.html) - Hướng dẫn cài đặt và sử dụng chi tiết
- [Tính năng](https://mrtinhnguyen.github.io/NotebookLM2PPT/features.html) - Tìm hiểu tất cả các tính năng mạnh mẽ
- [Tối ưu hóa MinerU](https://mrtinhnguyen.github.io/NotebookLM2PPT/mineru.html) - Tìm hiểu cách đạt kết quả tốt nhất
- [Chi tiết triển khai](https://mrtinhnguyen.github.io/NotebookLM2PPT/implementation.html) - Tiết lộ các nguyên tắc kỹ thuật
- [Nhật ký cập nhật](https://mrtinhnguyen.github.io/NotebookLM2PPT/changelog.html) - Xem lịch sử phiên bản

---

## 📄 Giấy phép mã nguồn mở và Phản hồi

Dự án này được cấp phép theo [MIT License](LICENSE).
Hoan nghênh gửi [Issues](https://github.com/mrtinhnguyen/NotebookLM2PPT/issues) hoặc Pull Request。
