# Hướng dẫn biên dịch
- Tải mã nguồn
- Tạo một môi trường, chỉ cài đặt các phụ thuộc của dự án này và pyinstaller
- Tham khảo cấu hình upx để cấu hình upx, được dùng để nén tập tin exe
- Biên dịch
```
pyinstaller --clean -F -w -n notebooklm2ppt --optimize=2 --collect-all spire.presentation main.py 
pyinstaller -D -w -n notebooklm2ppt --optimize=2 main.py
pyinstaller --clean -D -w -n notebooklm2ppt --optimize=2 --collect-all spire.presentation main.py

python -m nuitka --standalone main.py
git log -n 10 > log.txt
```