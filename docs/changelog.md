# Changelog

Tài liệu này ghi lại tất cả lịch sử cập nhật phiên bản của NotebookLM2PPT.

## [v0.7.0] - 2026-01-29

### ⚙️ Quản lý cấu hình và tối ưu hóa trải nghiệm người dùng

- **Thêm hệ thống quản lý cấu hình**: Hỗ trợ lưu nhớ các cài đặt của người dùng, tự động lưu và tải lại các cài đặt tác vụ lần cuối (đường dẫn đầu ra, DPI, ngôn ngữ, v.v.)
- **Tọa độ chụp ảnh tùy chỉnh**: Thêm chức năng tùy chỉnh tọa độ xu hướng vùng chụp, hỗ trợ cài đặt xu hướng trong GUI, và tự động ngăn chặn vượt quá biên màn hình
- **Chức năng thống nhất phông chữ**: Hỗ trợ thay thế công thống nhất phông chữ PPT ở chế độ tối ưu hóa MinerU, nâng cao tính nhất quán thẩm mỹ của tài liệu

### 🚀 Năng lực xử lý hàng loạt

- **Ghép cặp tác vụ thông minh**: Thêm hộp thoại ghép cặp tác vụ hàng loạt, hỗ trợ hai chế độ ghép cặp thông minh và ghép cặp theo thứ tự
- **Tối ưu hóa hướng dẫn ghép cặp tệp**: Cải thiện logic phát hiện trạng thái ghép cặp JSON, phân biệt giữa "Đã ghép cặp" và "không có JSON", và tăng cường kiểm tra tính hợp lệ khi thêm tác vụ
- **Cải tiến chức năng kéo thả**: Giao diện thêm hàng loạt hỗ trợ kéo tệp, nâng cao tiện lợi hoạt động
- **Tối ưu hóa quản lý hàng đợi**: Tối ưu hóa hiển thị hàng đợi tác vụ, hỗ trợ phân biệt giữa tệp đầu ra phiên bản được tối ưu hóa và phiên bản không tối ưu hóa

### 🎨 GUI và quốc tế hóa

- **Cảnh chỉnh bố cục UI**: Chuyển chọn ngôn ngữ đến khu vực cài đặt toàn cục, nâng cao tính tổ chức của các mục cài đặt
- **Nâng cao tính ổn định tương tác**: Sửa chữa vấn đề an toàn luồng trong chức năng kéo, giới thiệu cơ chế hàng đợi; tối ưu hóa hành vi hộp thoại, đổi thành hiển thị không phương thức để nâng cao độ mượt mà tương tác
- **Hoàn tất quốc tế hóa**: Thêm các khóa dịch cho các tài liệu tự động hóa, quản lý tác vụ, v.v., hoàn thành hỗ trợ đa ngôn ngữ Trung - Việt

### 🛠️ Ổn định và cải tiến thuật toán

- **Sửa chữa điều khiển tính chảy**: Sửa chữa vấn đề điều khiển lệ tính quá trình tối ưu hóa PPT, nâng cao độ chính xác và xóa bỏ nền lịch thừa cạnh
- **Tối ưu hóa xử lý nền**: Sắp xếp lại thứ tự xử lý nền, giải quyết vấn đề phủ nạp hình ảnh, và tối ưu hóa độ lệch của cảm nhận đa dạng thế tăng đến 15

---

## [v0.6.6] - 2026-01-28

### 📦 Hỗ trợ tác vụ hàng loạt

- **Hàng đợi tác vụ mới**: Hỗ trợ thêm, chỉnh sửa, xóa và thực hiện theo thứ tự ở phía sau các tác vụ chuyển đổi PDF hàng loạt
- **Kéo thả nhiều tệp**: Hỗ trợ kéo cùng lúc nhiều tệp PDF và JSON để xử lý hàng loạt

### ⚡ Hiệu suất và tối ưu hóa tự động hóa

- **Phản ứng cực tốc**: Xóa các độ trễ không cần thiết trong quy trình chụp ảnh (giảm từ 1-2s xuống 0s), đáng kể cải thiện tốc độ thực hiện tự động hóa
- **Phát hiện môi trường**: Thêm phát hiện trạng thái chạy của Microsoft PC Manager, cung cấp hướng dẫn cài đặt khi chưa chạy

### 🛠️ Sửa chữa và cải tiến

- **Tối ưu hóa hiển thị**: Thêm đệm cạnh cho hiển thị hình ảnh toàn màn hình, sửa chữa vấn đề đường viền đen ở cạnh màn hình
- **Sửa chữa cấu hình**: Sửa chữa vấn đề các biến UI không được cập nhật đồng bộ sau khi GUI tải cấu hình
- **Hoàn thiện tài liệu**: Cập nhật tài liệu thuật toán xử lý nền, giải thích chi tiết nguyên tắc phát hiện đa dạng cạnh

---

## [v0.6.5] - 2026-01-27

### 🔄 Hỗ trợ WPS

- Thêm hỗ trợ cho ứng dụng PPT mặc định là WPS
- Trước đây chỉ có thể nhận dạng PowerPoint là mặc định
- Cảm ơn MadCatPX vì đã đóng góp

---

## [v0.6.4] - 2026-01-26

### 🌍 Hỗ trợ đa ngôn ngữ

- **Thêm hỗ trợ đa ngôn ngữ**
- Thêm mô-đun i18n mới, chứa các tệp dịch tiếng Trung và Anh
- Thêm chức năng chuyển đổi ngôn ngữ trong GUI, hỗ trợ Tiếng Trung Giản Thể và Tiếng Anh
- Tái cấu trúc mã GUI để sử dụng thay thế văn bản động, tất cả văn bản giao diện có thể dịch
- Cập nhật số phiên bản lên 0.6.4 để phản ánh các tính năng mới

---

## [v0.6.3] - 2026-01-25

### 🛠️ Nâng cao ổn định

- **Nâng cao ổn định nhẹ**, nếu sử dụng bình thường không cần nâng cấp
- Cải thiện chức năng phát hiện cửa sổ PPT, tăng hỗ trợ cho đường dẫn đầy đủ
- Tối ưu hóa logic đóng cửa sổ trình khám phá tài nguyên, hỗ trợ khớp đường dẫn chính xác
- Thêm giao diện COM để lấy thông tin tệp PPT, cải thiện ổn định

---

## [v0.6.2] - 2026-01-23

### 🎨 Cải tiến phương pháp sửa chữa hình ảnh và tối ưu hóa chức năng

Bản cập nhật này tập trung vào nâng cao sâu chức năng sửa chữa hình ảnh và tối ưu hóa trải nghiệm người dùng tổng thể, cung cấp các phương pháp sửa chữa chuyên nghiệp hơn và chế độ sử dụng linh hoạt hơn.

#### Tối ưu hóa lõi

**6 phương pháp sửa chữa hình ảnh chuyên nghiệp**
Tái cấu trúc mô-đun sửa chữa hình ảnh, cung cấp lựa chọn nhiều thuật toán sửa chữa:
- **Làm mịn thông minh (Khuyên dùng)** - Hiệu ứng tổng hợp tốt nhất, phù hợp với hầu hết các khoảnh khắc xóa văn bản, hình mờ
- **Điền giá trị trung bình cạnh** - Lấy màu sắc pixel trung bình xung quanh để điền, thích hợp cho nền đơn sắc hoặc đơn giản
- **Điền nhanh siêu ngoài** - Điền trực tiếp màu nền duy nhất, chỉ thích hợp cho mục tiêu siêu tối giản, tốc độ nhanh nhất
- **Sửa chữa lớp trong ngoài** - Sửa chữa lớp từ ngoài vào, thích hợp với các đường gạch ngang hoặc kéo dài tháp
- **Nội suy chuyển tiếp dần** - Tính toán chuyển tiếp bề mặt mịn, thích hợp với nền có dải màu
- **Sửa chữa điều hòa kép với ánh sáng bóng** - Khối lượng tính toán lớn, tốc độ chậm hơn, nhưng có thể tốt hơn bài tập ánh sáng bóng tính liên tục

#### Cải tiến chức năng

- **🖼️ Chế độ chỉ hình ảnh**: Thêm tùy chọn chế độ chỉ hình ảnh mới, cho phép ngư dân bỏ qua chức năng vòng tròn thông minh
  - Chèn trực tiếp hình ảnh PNG đã xóa hình mờ vào PPT
  - Tốc độ tạo nhanh hơn, nhưng nội dung trong PPT không thể chỉnh sửa được
  - Thêm hộp thoại xác nhận, đảm bảo người dùng hiểu các tính năng chế độ

- **📖 Cửa sổ hướng dẫn phương pháp sửa chữa**: Thêm hộp thoại hướng dẫn chi tiết phương pháp sửa chữa hình ảnh, giúp người dùng hiểu các tính năng và trường hợp sử dụng của các phương pháp khác nhau

#### Tối ưu hóa bố cục GUI

- Tái cấu trúc bố cục giao diện mô-đun sửa chữa hình ảnh, cung cấp trải nghiệm chọn phương pháp trực quan hơn
- Tất cả cửa sổ (cửa sổ chính, hộp thoại) mặc định hiển thị ở giữa, cải thiện trải nghiệm người dùng
- Sử dụng nhận dạng tiếng Anh để lưu cấu hình phương pháp sửa chữa, cải thiện khả năng tương thích

---

## [v0.6.1] - 2026-01-23

### 🖼️ Chế độ chỉ hình ảnh

- Thêm tùy chọn chế độ chỉ hình ảnh mới, cho phép người dùng bỏ qua chức năng vòng tròn thông minh
- Chèn trực tiếp hình ảnh PNG đã xóa hình mờ vào PPT
- Chế độ này tạo nhanh hơn nhưng nội dung không thể chỉnh sửa
- Thêm hộp thoại xác nhận liên quan và xử lý logic

---

## [v0.6.0] - 2026-01-23

### 💎 Phiên bản lõi: Hướng tới siêu nhẹ cực tính

Trong v0.6.0, chúng tôi đã hoàn thành việc tái cấu trúc cơ bản toàn diện nhất kể từ khi dự án phát hành. Bằng việc hoàn toàn loại bỏ hai thư viện nặng OpenCV và Scikit-learn, không chỉ giải quyết vấn đề khởi động chậm do gói nhị phân quá lớn, mà còn nén lại thể tích chương trình biên dịch đến mức cực.

#### 🚀 Tối ưu hóa hiệu suất và kinh trúc

**1. Toàn bộ "giảm cân" thư viện phụ thuộc**
- **Loại bỏ Scikit-learn**: Thay thế phát hiện đa dạng cạnh DBSCAN ban đầu bằng triển khai Numpy gốc hiệu suất cao
- **Loại bỏ OpenCV**: Muộn hiển thị hình ảnh toàn màn hình hoàn toàn sang Tkinter
- **Lợi ích thể tích**: Kích thước tệp .exe hoặc nhị phân biên dịch giảm đáng kể, tốc độ khởi động lạnh và tiêu thụ bộ nhớ tối ưu đáng kể

**2. Nâng cấp thuật toán lõi**
- **Sửa chữa hình ảnh 2.0**: Sử dụng logic véc-tơ hóa Numpy mới thay thế thuật toán nhóm, trong khi duy trì độ chính xác, đáng kể cải thiện hiệu quả xử lý hình ảnh kích thước lớn
- **Phát hiện đa dạng cạnh**: Thêm công cụ tính toán đa dạng cạnh mới, tối ưu hóa đặc biệt hiệu ứng điền cho các vùng nền đơn sắc trong tập diễn lamppet, chuyển tiếp tự nhiên hơn

#### 🆕 Tính năng mới và cải tiến

**Logic tương tác**
- Thêm chức năng "dừng tinh kiêu ngay lập tức"
- Cho trình xem hình ảnh thêm hỗ trợ phím ESC toàn cầu
- Dù ở quá trình chụp ảnh, xử lý hay quy trình chuyên đổi, tất cả có thể ngay lập tức gián đoạn tác vụ qua phím ESC hoặc tín hiệu bên ngoài

**Cải tiến xử lý chút lại PPT**
- Tối ưu hóa logic nhận dạng và điền khối văn bản và khối hình ảnh PPT
- Sửa chữa vấn đề "hình ảnh hai lớp", đảm bảo mỗi khối yếu tố tạo ra lớp độc nhất và đúng trong tập tính

**Điều chỉnh trải nghiệm GUI**
- Điều chỉnh kích thước cửa sổ mặc định, nhằm đạt tỷ lệ hình ảnh tốt nhất trên các màn hình có độ phân giải khác nhau

#### 🛠️ Bảo trì nội bộ

- Cập nhật hệ thống xây dựng: Đồng bộ hóa-mã lệnh biên dịch pyinstaller, loại bỏ Hook không cần thiết và đường dẫn đóng gói
- Nâng cao độ vững chắc: Thêm các trường hợp kiểm tra chuyên biệt cho phát hiện đa dạng cạnh, đảm bảo ổn định thuật toán trong các nền phức tạp khác nhau

---

## [v0.5.5] - 2026-01-23

### 🎯 Tối ưu hóa xử lý khối văn bản PPT

- Thêm xử lý khối hình ảnh trong xử lý tinh chỉnh PPT
- Đảm bảo tất cả khối văn bản và khối hình ảnh có thể được điền đúng cách
- Sửa chữa vấn đề "hình ảnh hai lớp", bây giờ sẽ không xuất hiện hình ảnh hai lớp

---

## [v0.5.4] - 2026-01-23

### 📂 Chức năng nhớ hộp thoại tệp

- Thêm nút "Mở" trong khu vực chọn tệp, để truy cập nhanh thư mục đầu ra
- Cải thiện xử lý phạm vi trang, hỗ trợ dấu chấm câu Trung Quốc và tự động tạo tên tệp với phạm vi trang
- Tối ưu hóa định dạng tên tệp đầu ra PPT, bao gồm thông tin phạm vi trang
- Thêm chức năng nhớ thư mục tệp mở lần cuối, cải thiện trải nghiệm người dùng

---

## [v0.5.3] - 2026-01-19

### 📦 Bổ sung phụ thuộc

- Thêm scikit-learn vào các phụ thuộc dự án
- Cập nhật số phiên bản trong pyproject.toml thành 0.5.3
- Hủy bình luận lệnh tải lên twine trong build.cmd

---

## [v0.5.2] - 2026-01-17

### 🎨 Cải tiến hiệu ứng tối ưu hóa MinerU

- Sử dụng thuật toán nhóm DBSCAN thay thế tính toán độ lệch chuẩn để phát hiện đa dạng cạnh, cải thiện độ chính xác
- Loại bỏ hàm tính toán chênh lệch màu bốn điểm không còn sử dụng
- Điều chỉnh logic xử lý nền khối văn bản, quyết định có nên điền màu thuần chủng dựa trên kết quả nhóm

---

## [v0.5.1] - 2026-01-14

### 🐛 Sửa chữa sự cố chương trình bị sập

- Xử lý tình huống tập diễn lamppet vô nền
- Thêm xử lý cho tình huống vô nền, tránh chương trình sập
- Khi tập diễn lamppet vô nền, bỏ qua các thao tác liên quan trong logic thay thế nền

---

## [v0.5.0] - 2026-01-14

### 🆕 Tối ưu hóa xử lý hậu kỳ PPT dựa trên MinerU (Cập nhật thử nghiệm quan trọng)

Thêm chức năng tối ưu hóa xử lý hậu kỳ PPT dựa trên MinerU mới, bao gồm lọc hộp văn bản thông minh, thống nhất phông chữ, thay thế hình ảnh chất lượng cao và xử lý nền thông minh.

#### Chức năng lõi

- **✨ Lọc hộp văn bản thông minh**: Tự động xác định và giữ lại các hộp văn bản liên quan dựa trên thuật toán IOU, xóa các hộp văn bản dư thừa
- **🎨 Xử lý thống nhất phông chữ**: Tự động thống nhất tất cả phông chữ hộp văn bản thành "Microsoft YaHei"
- **🖼️ Thay thế hình ảnh chất lượng cao**: Trích xuất hình ảnh gốc độ phân giải cao từ JSON MinerU, thay thế hình ảnh chụp ảnh
- **🎭 Xử lý nền thông minh**: Xử lý nền thông minh dựa trên tính năng nội dung, đạt kết quả hình ảnh tốt nhất

#### Cập nhật GUI

- Cập nhật GUI để hỗ trợ nhập tệp MinerU JSON
- Thêm hộp thoại chào mừng khởi động, hiển thị thông tin phần mềm và liên kết GitHub, cung cấp tùy chọn không hiển thị lại

#### Hoàn thiện tài liệu

- Thêm tài liệu hướng dẫn liên quan
- Thêm compare.png và compare2.png làm hình ảnh ví dụ so sánh
- Tái cấu trúc cấu trúc mã, di chuyển ppt_combiner.py sang thư mục tiện ích
- Cập nhật README giải thích chi tiết phương pháp sử dụng chức năng tối ưu hóa MinerU và lợi ích
- Thêm tài liệu mineru-technical-details.md giải thích chi tiết chi tiết triển khai kỹ thuật

---

## [v0.4.0] - 2026-01-13

### 🖥️ Giao diện người dùng đồ họa (GUI)

- Thiết kế lại bố cục GUI, thêm chức năng lưu và tải cấu hình
- Loại bỏ chế độ CLI, tập trung vào trải nghiệm GUI
- Tối ưu hóa logic hiệu chuẩn bù nút, tự động lưu cấu hình
- Cải thiện đầu ra nhật ký và tin nhắn gợi ý người dùng
- Cập nhật tài liệu README, loại bỏ nội dung lỗi thời
- Tăng số phiên bản lên 0.4.0

#### Cải tiến chức năng

- Thêm chức năng chọn phạm vi trang
- Cải thiện quy trình hiệu chuẩn bù nút
- Thêm nhập phạm vi trang và các tùy chọn hiệu chuẩn bù nút vào giao diện GUI

---

## [v0.3.0] - 2025-12-31

### ⚙️ Phiên bản Quản lý PC và Chức năng bù nút hoàn thành

- Thêm chức năng phát hiện phiên bản Quản lý PC
- Thêm chức năng bù nút hoàn thành mới, cải thiện độ chính xác tự động hóa
- Cập nhật lệnh biên dịch và số phiên bản lên 0.3.0

---

## [v0.2.0] - 2025-12-22

### 🖱️ Giao diện người dùng đồ họa (GUI)

- Thêm hỗ trợ giao diện người dùng đồ họa (GUI)
- Cho phép người dùng chọn tệp PDF qua kéo thả và đặt các tham số chuyên đổi
- Sửa chữa tính toán vị trí nút trong tự động hóa chụp ảnh
- Cập nhật README.md, thêm hướng dẫn cài đặt và sử dụng
- Thêm tài liệu hướng dẫn biên dịch
- Cập nhật các phụ thuộc, đảm bảo hỗ trợ chức năng kéo trên nền tảng Windows
- Sửa lại định dạng tải lên tệp trong lệnh xây dựng

---

## [v0.1.0] - 2025-12-22

### 🎉 Phiên bản ban đầu

Triển khai chức năng cơ bản của công cụ chuyên đổi PDF sang PPT:

- Thêm chức năng cơ bản chuyên đổi tệp PDF thành hình ảnh PNG và xử lý thành bản trình chiếu PowerPoint
- Tích hợp trình xem hình ảnh, hỗ trợ hiển thị hình ảnh toàn màn hình
- Sử dụng công cụ vòng tròn thông minh Microsoft để triển khai tự động hóa chụp ảnh
- Thêm chức năng sửa chữa hình ảnh, dùng để xóa hình mờ trong hình ảnh
- Tạo các hàm tiện ích, dùng để xử lý chế độ xem hình ảnh, sửa chữa và tự động hóa chụp ảnh
- Phát triển công cụ hợp nhất PPT, hợp nhất các tệp PPT được tạo trong khi giữ lại thiết kế ban đầu
- Cập nhật requirements.txt, bao gồm các phụ thuộc cần thiết của dự án
- Thêm tài liệu mô-đun và kiểm soát phiên bản, để cải thiện khả năng bảo trì

---

## Ghi chú phiên bản

Tài liệu này tuân theo định dạng [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/),
Số phiên bản tuân theo thông quy [Semantic Versioning](https://semver.org/lang/zh-CN/).
