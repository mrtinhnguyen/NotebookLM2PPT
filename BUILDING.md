# Hướng dẫn nhanh: Build và Release

Tài liệu này cung cấp các lệnh thông dụng và quy trình nhanh để phát triển, xây dựng và phát hành NotebookLM2PPT.

## Khởi tạo môi trường (Chỉ lần đầu)

```bash
# Clone kho lưu trữ
git clone https://github.com/mrtinhnguyen/NotebookLM2PPT.git
cd NotebookLM2PPT

# Tạo và kích hoạt môi trường ảo
python -m venv venv
venv\Scripts\activate.bat

# Cài đặt phụ thuộc
pip install -r requirements.txt
pip install build twine pyinstaller
```

## Chạy cục bộ

```bash
# Kích hoạt môi trường ảo (nếu chưa)
venv\Scripts\activate.bat

# Chạy chương trình
python main.py

# Hoặc dùng script
.\build-helper.cmd         # Windows CMD
.\build-helper.ps1 -Action run  # PowerShell
```

## Kiểm tra

```bash
# Kiểm tra cú pháp
python -m py_compile notebooklm2ppt\*.py
python -m py_compile notebooklm2ppt\utils\*.py

# Kiểm tra import
python -c "import notebooklm2ppt; print('OK')"

# Kiểm tra GUI
python main.py  # Và thử các tính năng thủ công

# Dùng script
.\build-helper.cmd test
.\build-helper.ps1 -Action test
```

## Xây dựng gói Python (Wheel)

```bash
# Dọn dẹp bản dựng cũ
rmdir /s /q build dist *.egg-info 2>nul

# Xây dựng
python -m build

# Kiểm tra
twine check dist\*

# Kết quả: dist\notebooklm2ppt-X.X.X-py3-none-any.whl

# Dùng script
.\build-helper.cmd build
.\build-helper.ps1 -Action build
```

## Xây dựng tệp exe (PyInstaller)

### Tùy chọn 1: One-file (dễ phân phối)

```bash
pyinstaller --clean -F -w -n notebooklm2ppt --optimize=2 main.py

# Kết quả: dist\notebooklm2ppt.exe
# Kích thước: ~200-300 MB
# Tốc độ khởi động: Chậm (giải nén trước)

# Dùng script
.\build-helper.cmd exe-single
.\build-helper.ps1 -Action exe-single
```

### Tùy chọn 2: One-folder (khởi động nhanh)

```bash
pyinstaller --clean -D -w -n notebooklm2ppt --optimize=2 --collect-all spire.presentation main.py

# Kết quả: dist\notebooklm2ppt\notebooklm2ppt.exe
# Và các file phụ thuộc trong cùng thư mục
# Tốc độ khởi động: Nhanh hơn

# Dùng script
.\build-helper.cmd exe-folder
.\build-helper.ps1 -Action exe-folder
```

## Quy trình xây dựng đầy đủ

```bash
# Dọn + Kiểm tra + Xây dựng
.\build-helper.cmd full
.\build-helper.ps1 -Action full

# Hoặc thủ công
rmdir /s /q build dist *.egg-info
python -m py_compile notebooklm2ppt\*.py
python -m py_compile notebooklm2ppt\utils\*.py
python -m build
twine check dist\*
```

## Một số lệnh hữu ích

```bash
# Xem danh sách các lệnh
.\build-helper.cmd
.\build-helper.ps1

# Dọn dẹp
python -m pip cache purge
rmdir /s /q venv __pycache__ build dist *.egg-info

# Kiểm tra gói
twine check dist\*

# Xem version hiện tại
findstr /c:"version = " pyproject.toml

# Xem các gói đã cài
pip list

# Cập nhật pip
python -m pip install --upgrade pip setuptools wheel
```

## Phát hành

### 1. Chuẩn bị

```bash
# Cập nhật phiên bản trong pyproject.toml
# Ví dụ: version = "1.1.3"

# Cập nhật docs/changelog.md

# Xây dựng lại
.\build-helper.cmd full

# Kiểm tra tệp thực thi (nếu có)
dist\notebooklm2ppt.exe
```

### 2. Tạo tag Git

```bash
# Xem tag hiện tại
git tag

# Tạo tag mới
git tag -a v1.1.3 -m "Release version 1.1.3"

# Đẩy tag
git push origin v1.1.3

# Hoặc đẩy tất cả tag
git push origin --tags
```

### 3. Tải lên PyPI

```bash
# Kiểm tra lần nữa
twine check dist\*

# Test upload (tuỳ chọn)
twine upload --repository testpypi dist\*

# Upload chính thức
twine upload dist\*

# Nhập thông tin PyPI khi yêu cầu
# (Hoặc sử dụng token API - tốt hơn)
```

### 4. Tạo GitHub Release

```bash
# Trên trình duyệt:
# 1. Vào https://github.com/mrtinhnguyen/NotebookLM2PPT/releases
# 2. Nhấp "Create a new release"
# 3. Chọn tag: v1.1.3
# 4. Tiêu đề: "Release v1.1.3"
# 5. Mô tả: Sao chép từ CHANGELOG
# 6. Tải lên tệp .exe (nếu có)
# 7. Phát hành
```

## Xử lý sự cố nhanh

| Lỗi | Giải pháp |
|-----|----------|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| `PyInstaller not found` | `pip install pyinstaller` |
| `twine not found` | `pip install twine` |
| `Could not find module` | Thêm `--hidden-import=xxx` vào PyInstaller |
| `pyinstaller: command not found` | Restart terminal hoặc activate venv lại |
| `egg-info not found` | `python -m build` tự động tạo |

## Chi tiết tệp cấu hình

### pyproject.toml
```toml
[project]
name = "notebooklm2ppt"
version = "1.1.3"              # ← Cập nhật ở đây khi phát hành
description = "..."
requires-python = ">=3.8"
dependencies = [...]           # ← Thêm phụ thuộc mới ở đây
```

### docs/changelog.md
```markdown
## [v1.1.3] - 2026-02-08

### ✨ Tính năng mới
- ...

### 🐛 Sửa lỗi
- ...

### 📚 Cải thiện tài liệu
- ...
```

## Lưu ý quan trọng

1. **Luôn kiểm tra trước phát hành**
   - Chạy đầy đủ `full build`
   - Kiểm tra tệp thực thi
   - Thử cài đặt từ PyPI

2. **Phiên bản phải theo quy tắc Semantic Versioning**
   - MAJOR.MINOR.PATCH
   - Ví dụ: 1.1.3

3. **Luôn tạo tag Git trước PyPI upload**
   - Điều này giúp theo dõi lịch sử

4. **Cập nhật CHANGELOG trước mỗi phát hành**
   - Người dùng cần biết thay đổi gì

5. **Test trên máy tính khác**
   - Cài đặt từ PyPI trước phát hành chính thức
   - Kiểm tra tệp exe trên máy không có Python

## Tài liệu chi tiết

Xem `docs/development-guide.md` để có hướng dẫn chi tiết hơn.

## Support

Nếu gặp vấn đề:
1. Kiểm tra [GitHub Issues](https://github.com/mrtinhnguyen/NotebookLM2PPT/issues)
2. Tạo issue mới nếu cần thiết
3. Liên hệ tác giả
