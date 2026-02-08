# Hướng dẫn phát triển, xây dựng và phát hành

Tài liệu này cung cấp hướng dẫn chi tiết để thiết lập môi trường phát triển, xây dựng dự án cục bộ, kiểm tra và phát hành phiên bản.

## Mục lục

1. [Thiết lập môi trường phát triển](#thiết-lập-môi-trường-phát-triển)
2. [Chạy cục bộ và phát triển](#chạy-cục-bộ-và-phát-triển)
3. [Xây dựng (Build)](#xây-dựng-build)
4. [Kiểm tra (Testing)](#kiểm-tra-testing)
5. [Chuẩn bị phát hành](#chuẩn-bị-phát-hành)
6. [Đóng gói và phát hành](#đóng-gói-và-phát-hành)

---

## Thiết lập môi trường phát triển

### Yêu cầu hệ thống

- **Windows 10/11** (dự án hỗ trợ Windows)
- **Python 3.8+** (khuyến nghị 3.10 hoặc cao hơn)
- **Git** để quản lý mã nguồn
- **PowerPoint hoặc WPS Office** (để kiểm tra tính năng GUI)
- **Microsoft PC Manager** (để kiểm tra tính năng Smart Select)

### Bước 1: Clone và thiết lập thư mục

```bash
# Clone kho lưu trữ
git clone https://github.com/mrtinhnguyen/NotebookLM2PPT.git
cd NotebookLM2PPT

# Xem danh sách nhánh
git branch -a

# Chuyển sang nhánh phát triển (nếu có)
git checkout develop
```

### Bước 2: Tạo môi trường ảo (Virtual Environment)

```bash
# Tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường ảo
# Trên Windows CMD:
venv\Scripts\activate.bat

# Hoặc trên Windows PowerShell:
venv\Scripts\Activate.ps1

# Xác nhận môi trường đã được kích hoạt (dấu nhắc sẽ bắt đầu bằng (venv))
```

### Bước 3: Cài đặt các phụ thuộc

```bash
# Cập nhật pip, setuptools và wheel
python -m pip install --upgrade pip setuptools wheel

# Cài đặt các phụ thuộc của dự án
pip install -r requirements.txt

# Cài đặt các công cụ phát triển
pip install build twine pyinstaller nuitka

# (Tùy chọn) Cài đặt các công cụ kiểm tra
pip install pytest black flake8 isort
```

### Bước 4: Kiểm tra cài đặt

```bash
# Kiểm tra phiên bản Python
python --version

# Kiểm tra các gói chính đã cài đặt
pip list | findstr "pymupdf python-pptx"

# Kiểm tra mô-đun GUI
python -c "import tkinter; print('Tkinter OK')"
```

---

## Chạy cục bộ và phát triển

### Chạy chương trình từ mã nguồn

```bash
# Chắc chắn môi trường ảo đã được kích hoạt
# Sau đó chạy:
python main.py
```

Cửa sổ GUI sẽ xuất hiện. Bây giờ bạn có thể:
- Chọn tệp PDF
- Cấu hình các tùy chọn
- Kiểm tra các tính năng khác nhau

### Chạy qua CLI

```bash
# Sau khi cài đặt dự án ở chế độ phát triển
pip install -e .

# Chạy lệnh từ bất kỳ nơi nào
notebooklm2ppt
```

### Chạy qua các script test

```bash
# Chạy kiểm tra so sánh
python tests/compare_result.py <pdf_file> <pptx1> <pptx2>

# Xem các tệp kiểm tra khác
dir tests/
```

### Cấu trúc dự án để tham khảo

```
NotebookLM2PPT/
├── notebooklm2ppt/          # Gói chính
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              # Command-line interface
│   ├── config_defaults.py  # Cấu hình mặc định
│   ├── gui.py              # Giao diện đồ họa chính
│   ├── pdf2png.py          # Chuyên đổi PDF sang PNG
│   ├── i18n/               # Quốc tế hóa
│   │   ├── en.py           # Tiếng Anh
│   │   └── zh_cn.py        # Tiếng Trung
│   └── utils/              # Các hàm tiện ích
│       ├── coordinate_utils.py
│       ├── edge_diversity.py
│       ├── image_inpainter.py
│       ├── image_viewer.py
│       ├── inpaint_methods.py
│       ├── pp_ocr.py
│       ├── ppt_combiner.py
│       ├── ppt_creater.py
│       ├── ppt_refiner.py
│       ├── process_checker.py
│       └── screenshot_automation.py
├── tests/                   # Các kiểm tra tự động
├── docs/                    # Tài liệu
└── main.py                  # Điểm vào chính
```

---

## Xây dựng (Build)

### Tùy chọn 1: Xây dựng gói Python (Wheel + Source Distribution)

Phương pháp này tạo các gói có thể cài đặt qua pip.

```bash
# Đảm bảo bạn ở thư mục gốc của dự án
cd d:\TonyX.Dev\AI\NotebookLM2PPT

# Xây dựng gói
python -m build

# Kiểm tra các tệp đã được tạo
# Trong thư mục dist/ sẽ có:
# - notebooklm2ppt-X.X.X-py3-none-any.whl
# - notebooklm2ppt-X.X.X.tar.gz
dir dist/
```

**Ưu điểm:**
- Kích thước nhỏ
- Dễ dàng cài đặt trên các máy tính khác nhau
- Hỗ trợ tự động cập nhật

**Nhược điểm:**
- Yêu cầu Python được cài đặt trên máy người dùng
- Người dùng cần cài đặt các phụ thuộc

### Tùy chọn 2: Xây dựng tệp thực thi độc lập (EXE) - PyInstaller

Phương pháp này tạo tệp .exe độc lập không cần Python.

#### 2a. Cách đơn giản (One-file)

```bash
# Xây dựng tệp thực thi đơn tệp
pyinstaller --clean -F -w -n notebooklm2ppt --optimize=2 main.py

# Kết quả sẽ ở: dist/notebooklm2ppt.exe
```

**Ưu điểm:**
- Chỉ có một tệp .exe
- Dễ phân phối

**Nhược điểm:**
- Khởi động chậm hơn (phải giải nén)
- Kích thước lớn (200-300 MB)

#### 2b. Cách advanced (One-folder)

```bash
# Xây dựng thư mục tệp thực thi với tất cả các phụ thuộc
pyinstaller --clean -D -w -n notebooklm2ppt --optimize=2 --collect-all spire.presentation main.py

# Kết quả sẽ ở: dist/notebooklm2ppt/
# Chạy: dist/notebooklm2ppt/notebooklm2ppt.exe
```

**Ưu điểm:**
- Khởi động nhanh hơn
- Dễ debug hơn

**Nhược điểm:**
- Là một thư mục (khó phân phối)

#### 2c. Xây dựng với nén UPX (không bắt buộc)

```bash
# Cài đặt UPX
choco install upx  # Nếu dùng Chocolatey
# Hoặc tải từ: https://upx.github.io/

# Xây dựng với nén
pyinstaller --clean -F -w -n notebooklm2ppt --optimize=2 -upx-dir="C:\path\to\upx" main.py
```

### Tùy chọn 3: Xây dựng với Nuitka (Nâng cao)

```bash
# Xây dựng với Nuitka (biên dịch thành C++)
python -m nuitka --standalone main.py

# Giả lập hoàn toàn
python -m nuitka --standalone --onefile main.py
```

**Ưu điểm:**
- Hiệu suất tốt hơn
- Khó reverse-engineer hơn

**Nhược điểm:**
- Thời gian biên dịch lâu
- Cần C++ compiler

---

## Kiểm tra (Testing)

### Kiểm tra cơ bản

```bash
# Kiểm tra cú pháp Python
python -m py_compile notebooklm2ppt/*.py
python -m py_compile notebooklm2ppt/utils/*.py

# Kiểm tra các import
python -c "import notebooklm2ppt; print('Import OK')"
```

### Kiểm tra GUI (Manual)

```bash
# Chạy GUI
python main.py

# Kiểm tra các tính năng sau:
# 1. Kéo thả tệp PDF
# 2. Chọn thư mục đầu ra
# 3. Cấu hình các tùy chọn
# 4. Chạy chuyên đổi
# 5. Kiểm tra tệp PPT đầu ra
```

### Kiểm tra chức năng chính

```bash
# Tạo thư mục kiểm tra
mkdir test_input test_output

# Chuyên đổi PDF đơn giản thành PPT
python -c "
from notebooklm2ppt.main import main
main()
"
```

### Kiểm tra phiên bản đóng gói

```bash
# Kiểm tra tệp thực thi
dist\notebooklm2ppt\notebooklm2ppt.exe

# Hoặc nếu xây dựng one-file:
dist\notebooklm2ppt.exe
```

### Kiểm tra linting (tuỳ chọn)

```bash
# Kiểm tra mã với flake8
flake8 notebooklm2ppt/ --max-line-length=120

# Định dạng mã với black
black notebooklm2ppt/

# Sắp xếp import với isort
isort notebooklm2ppt/
```

---

## Chuẩn bị phát hành

### Kiểm tra danh sách

```bash
# 1. Cập nhật số phiên bản trong pyproject.toml
# Ví dụ: version = "1.1.2" -> "1.1.3"

# 2. Cập nhật CHANGELOG/changelog.md
# Thêm các mục mới dưới phiên bản mới

# 3. Kiểm tra README.md
# Đảm bảo tất cả liên kết và hướng dẫn đúng

# 4. Kiểm tra LICENSE
# Xác nhận rằng nó là MIT License

# 5. Chạy tất cả các bài kiểm tra
python -m pytest  # Nếu có các kiểm tra

# 6. Xây dựng lại từ đầu
rm -r build dist egg-info  # Xóa bản dựng cũ (nếu cần)
python -m build
```

### Tạo tag Git

```bash
# Xem thẻ hiện tại
git tag

# Tạo thẻ mới cho phiên bản
git tag -a v1.1.3 -m "Release version 1.1.3"

# Đẩy thẻ lên GitHub
git push origin v1.1.3

# Hoặc đẩy tất cả các thẻ
git push origin --tags
```

### Cập nhật tệp metadata

```bash
# Đảm bảo pyproject.toml có thông tin chính xác:
# - version
# - description
# - author
# - urls (Homepage, Repository, Issues)

# Kiểm tra tệp MANIFEST.in (nếu có)
# Đảm bảo tất cả các tệp cần thiết được bao gồm

# Kiểm tra .gitignore
# Đảm bảo tệp nhạy cảm không được commit
```

---

## Đóng gói và phát hành

### Bước 1: Xây dựng gói cuối cùng

```bash
# Làm sạch bản dựng cũ (tuỳ chọn)
rm -r build dist *.egg-info

# Xây dựng gói
python -m build

# Xác minh các tệp đã được tạo
dir dist/

# Đầu ra mong đợi:
# notebooklm2ppt-1.1.3-py3-none-any.whl
# notebooklm2ppt-1.1.3.tar.gz
```

### Bước 2: Kiểm tra gói (Tùy chọn nhưng được khuyến nghị)

```bash
# Cài đặt twine để kiểm tra và tải lên
pip install twine

# Kiểm tra gói trước khi tải lên
twine check dist/*

# Đầu ra mong đợi:
# Checking distribution notebooklm2ppt-1.1.3-py3-none-any.whl: Passed
# Checking distribution notebooklm2ppt-1.1.3.tar.gz: Passed
```

### Bước 3: Tải lên PyPI (Test trước)

```bash
# (Tuỳ chọn) Tải lên PyPI Test trước
twine upload --repository testpypi dist/*

# Kiểm tra tải lên trên: https://test.pypi.org/project/notebooklm2ppt/

# Cài đặt từ TestPyPI để kiểm tra
pip install -i https://test.pypi.org/simple/ notebooklm2ppt
```

### Bước 4: Tải lên PyPI Production

```bash
# Tải lên PyPI chính thức
twine upload dist/*

# Hoặc chỉ định kho lưu trữ
twine upload --repository pypi dist/*

# Bạn sẽ được yêu cầu nhập thông tin đăng nhập PyPI
# Hoặc sử dụng token API (được khuyến nghị)
```

### Bước 5: Phát hành trên GitHub

```bash
# Đảm bảo các thay đổi đã được commit
git status

# Commit nếu cần
git add .
git commit -m "Release v1.1.3"
git push origin main

# Tạo bản phát hành trên GitHub:
# 1. Vào https://github.com/mrtinhnguyen/NotebookLM2PPT/releases
# 2. Nhấp "Create a new release"
# 3. Chọn thẻ: v1.1.3
# 4. Tiêu đề: "Release v1.1.3"
# 5. Mô tả: Sao chép từ CHANGELOG
# 6. Tải lên tệp .exe (nếu có)
# 7. Nhấp "Publish release"
```

### Bước 6: Thông báo phát hành (Tùy chọn)

```bash
# Cập nhật tài liệu trên GitHub Pages (nếu có)
./publish_docs.sh

# Hoặc thủ công:
cd docs
npm install
npm run build
# Kiểm tra tệp đã xây dựng trong .vitepress/dist/
```

---

## Danh sách kiểm tra phát hành

Trước khi phát hành, hãy kiểm tra:

- [ ] Cập nhật số phiên bản trong `pyproject.toml`
- [ ] Cập nhật `docs/changelog.md`
- [ ] Tất cả các kiểm tra đã vượt qua
- [ ] README.md hiện tại và chính xác
- [ ] Mã không chứa `print()` statements chỉ dành cho debugging
- [ ] Xây dựng gói thành công (`python -m build`)
- [ ] Kiểm tra gói thành công (`twine check`)
- [ ] Kiểm tra tệp thực thi nếu được xây dựng
- [ ] Tạo thẻ Git (`git tag -a v1.1.3`)
- [ ] Đẩy thẻ (`git push origin v1.1.3`)
- [ ] Tải lên PyPI (`twine upload`)
- [ ] Tạo bản phát hành GitHub
- [ ] Thử cài đặt từ PyPI trên máy tính khác

---

## Xử lý sự cố

### Lỗi: "ModuleNotFoundError: No module named 'xxx'"

```bash
# Cài đặt lại các phụ thuộc
pip install -r requirements.txt
```

### Lỗi: "PyInstaller không tìm thấy mô-đun"

```bash
# Thêm thư mục vào PyInstaller
pyinstaller --hidden-import=spire.presentation main.py
```

### Lỗi: "Twine: 'egg-info' not found"

```bash
# Cài đặt lại build tools
pip install --upgrade build twine
python -m build
```

### EXE bị Windows Defender cảnh báo

```bash
# Đây là cảnh báo giả tính (false positive) do exe được tạo động
# Có thể ký mã hoặc yêu cầu loại trừ Windows Defender
```

---

## Tài nguyên bổ sung

- [Python Packaging Guide](https://packaging.python.org/)
- [PyPI Documentation](https://pypi.org/help/)
- [PyInstaller Manual](https://pyinstaller.org/en/stable/)
- [Git Tagging](https://git-scm.com/book/en/v2/Git-Basics-Tagging)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)

---

## Liên hệ và Hỗ trợ

Nếu bạn gặp vấn đề:

1. Kiểm tra [GitHub Issues](https://github.com/mrtinhnguyen/NotebookLM2PPT/issues)
2. Tạo một issue mới với chi tiết lỗi
3. Tham gia thảo luận cộng đồng
