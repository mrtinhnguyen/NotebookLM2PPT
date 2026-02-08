# Khắc Phục Sự Cố - NotebookLM2PPT

## Lỗi: ModuleNotFoundError: No module named 'fitz' (hoặc module khác)

### Nguyên nhân
Khi chạy `.exe` được tạo bởi PyInstaller, các module phụ thuộc không được đóng gói đầy đủ.

### Giải pháp

#### **Cách 1: Cài đặt từ PyPI (Khuyên dùng)**
Thay vì sử dụng `.exe`, cài đặt từ Python:

```bash
# Cài đặt với pip từ PyPI
pip install notebooklm2ppt

# Chạy
notebooklm2ppt
# hoặc
python -m notebooklm2ppt
```

#### **Cách 2: Chạy từ mã nguồn**
Nếu bạn có mã nguồn:

```bash
# Vào thư mục dự án
cd d:\TonyX.Dev\AI\NotebookLM2PPT

# Tạo và kích hoạt môi trường ảo
python -m venv venv
venv\Scripts\activate.bat

# Cài đặt phụ thuộc
pip install -r requirements.txt

# Chạy
python main.py
```

#### **Cách 3: Sử dụng build-helper cho PowerShell/CMD**
Scripta hỗ trợ chạy từ mã nguồn:

```powershell
# PowerShell
.\build-helper.ps1 -Action run

# CMD
.\build-helper.cmd run
```

---

## Lỗi: PyInstaller không tìm đủ dependencies

### Vấn đề
Một số thư viện như `pymupdf`, `spire.presentation`, `pywin32` không được PyInstaller phát hiện tự động.

### Giải pháp đơn giản nhất
**Hãy sử dụng Python wheels từ PyPI thay vì `.exe` được tạo cục bộ.**

Các `.exe` được tạo từ mã nguồn thường gặp vấn đề với các thư viện C++ hoặc thư viện

 dạng binary phức tạp.

### Nếu bạn vẫn muốn dùng .exe
Đặt hàng PyInstaller chính xác (cần quản lý truy cập):

```powershell
# Xuyên từ từng phụ thuộc một cách rõ ràng
python -m PyInstaller --clean -F -w `
  --hidden-import=fitz `
  --hidden-import=PIL `
  --hidden-import=skimage `
  --collect-all=spire.presentation `
  --collect-all=pymupdf `
  main.py
```

---

## Tóm Tắt: Các Cách Phát Hành Tốt Nhất

| Phương pháp | Ưu điểm | Nhược điểm | Khuyên không |
|-----------|---------|-----------|------------|
| **Python Wheel (.whl)** | ✅ Nhỏ (89 KB) ✅ Dễ cài ✅ Xứng đáng | Người dùng cần Python | ❌ Rất hiếm |
| **Source Dist (.tar.gz)** | ✅ Có mã | Người dùng cần Python | ❌ Khó sử dụng |
| ** .exe từ PyInstaller** | ✅ Không cần Python ❌ Rất difficultto với deps phức tạp | ❌ Lớn (100+ MB) ❌ Chậm khởi động | ❌ Với những lib heavy |
| **PyPI + pip** | ✅ Tiêu chuẩn ✅ Dễ cập nhật | Người dùng cần Python | ❌ Không |

---

## Khuyến Nghị để Phát Hành v1.1.3

1. **Tải lên PyPI** - `.whl` + `.tar.gz`
   ```bash
   python -m twine upload dist/notebooklm2ppt-1.1.3-*
   ```

2. **Tạo GitHub Release** - Tệp source + hướng dẫn cài đặt
   ```bash
   pip install notebooklm2ppt==1.1.3
   ```

3. **Tùy chọn**: Cung cấp `.exe` nếu bạn muốn
   - Nhưng phải test quá đầy đủ
   - Yêu cầu quản lý dependencies cặn kỹ

---

## Lệnh Nhanh

```bash
# Xem lỗi chi tiết từ .exe
.\dist\notebooklm2ppt.exe 2>&1 | Out-File error.log

# Cài từ mã nguồn (cách tốt nhất)
python main.py

# Cài từ PyPI
pip install notebooklm2ppt

# Dọn bản dựng cũ theo lệnh
.\build-helper.ps1 -Action clean
```
