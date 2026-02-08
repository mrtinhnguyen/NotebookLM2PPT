@echo off
REM ============================================================
REM NotebookLM2PPT Build Script
REM ============================================================
REM Tập lệnh này giúp xây dựng, kiểm tra và đóng gói dự án
REM
REM Sử dụng:
REM   build.cmd              - Hiển thị menu
REM   build.cmd test         - Chạy kiểm tra
REM   build.cmd build        - Xây dựng gói
REM   build.cmd exe-single   - Xây dựng exe 1 tệp
REM   build.cmd exe-folder   - Xây dựng exe thư mục
REM   build.cmd clean        - Dọn dẹp bản dựng
REM   build.cmd run          - Chạy từ mã nguồn
REM ============================================================

setlocal enabledelayedexpansion

REM Kiểm tra nếu có tham số
if "%1"=="" (
    goto menu
) else (
    goto %1
)

:menu
echo.
echo ============================================================
echo   NotebookLM2PPT - Build & Release Helper
echo ============================================================
echo.
echo Lựa chọn:
echo   1. test         - Chạy các kiểm tra cơ bản
echo   2. run          - Chạy chương trình từ mã nguồn
echo   3. build        - Xây dựng gói wheel + source dist
echo   4. exe-single   - Xây dựng exe 1 tệp (PyInstaller)
echo   5. exe-folder   - Xây dựng exe thư mục (PyInstaller)
echo   6. clean        - Dọn dẹp bản dựng cũ
echo   7. full         - Dọn dẹp + xây dựng + kiểm tra
echo   8. release      - Chuẩn bị cho phát hành
echo   0. Thoát
echo.
set /p choice="Chọn tùy chọn: "

if "%choice%"=="1" goto test
if "%choice%"=="2" goto run
if "%choice%"=="3" goto build
if "%choice%"=="4" goto exe-single
if "%choice%"=="5" goto exe-folder
if "%choice%"=="6" goto clean
if "%choice%"=="7" goto full
if "%choice%"=="8" goto release
if "%choice%"=="0" exit /b 0
goto menu

:test
echo.
echo [*] Kiểm tra cú pháp Python...
python -m py_compile notebooklm2ppt\*.py
if !errorlevel! neq 0 goto error
python -m py_compile notebooklm2ppt\utils\*.py
if !errorlevel! neq 0 goto error

echo [*] Kiểm tra import...
python -c "import notebooklm2ppt; print('✓ Import thành công')"
if !errorlevel! neq 0 goto error

echo [✓] Tất cả kiểm tra đã vượt qua!
pause
exit /b 0

:run
echo.
echo [*] Kích hoạt môi trường ảo...
call venv\Scripts\activate.bat
echo [*] Chạy chương trình...
python main.py
exit /b 0

:build
echo.
echo [*] Dọn dẹp bản dựng cũ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.egg-info rmdir /s /q *.egg-info

echo [*] Cải tổ số phiên bản từ pyproject.toml...
for /f "tokens=2 delims==" %%a in ('findstr /c:"version = " pyproject.toml') do (
    set version=%%a
)
echo    Phiên bản: !version!

echo [*] Xây dựng gói...
python -m build
if !errorlevel! neq 0 goto error

echo [*] Kiểm tra gói với twine...
twine check dist\*
if !errorlevel! neq 0 goto error

echo [✓] Xây dựng thành công!
echo.
echo    Các tệp được tạo:
dir dist\
pause
exit /b 0

:exe-single
echo.
echo [*] Xây dựng tệp exe đơn (one-file)...
echo.
echo    Tùy chọn:
echo    1. Cơ bản (quick)
echo    2. Với tối ưu hóa (slow, nhưng kích thước nhỏ hơn)
echo.
set /p exe_choice="Chọn: "

if "%exe_choice%"=="1" (
    echo [*] Xây dựng cơ bản...
    pyinstaller --clean -F -w -n notebooklm2ppt main.py
) else (
    echo [*] Xây dựng với tối ưu hóa...
    pyinstaller --clean -F -w -n notebooklm2ppt --optimize=2 main.py
)

if !errorlevel! neq 0 goto error

echo [✓] Tệp exe được tạo tại: dist\notebooklm2ppt.exe
echo [*] Kích thước tệp:
for %%f in (dist\notebooklm2ppt.exe) do (
    echo    %%~zf byte (%%~nf)
)
pause
exit /b 0

:exe-folder
echo.
echo [*] Xây dựng thư mục exe (one-folder)...
pyinstaller --clean -D -w -n notebooklm2ppt --optimize=2 --collect-all spire.presentation main.py

if !errorlevel! neq 0 goto error

echo [✓] Thư mục exe được tạo tại: dist\notebooklm2ppt\
echo [*] Để chạy, bấm đúp vào: dist\notebooklm2ppt\notebooklm2ppt.exe
pause
exit /b 0

:clean
echo.
echo [*] Dọn dẹp bản dựng...
if exist build rmdir /s /q build && echo    ✓ Xóa build/
if exist dist rmdir /s /q dist && echo    ✓ Xóa dist/
if exist *.egg-info (
    for /d %%d in (*.egg-info) do (
        rmdir /s /q "%%d" && echo    ✓ Xóa %%d
    )
)
if exist __pycache__ rmdir /s /q __pycache__ && echo    ✓ Xóa __pycache__
if exist .pyc del /q *.pyc && echo    ✓ Xóa .pyc files
echo [✓] Dọn dẹp hoàn tất!
pause
exit /b 0

:full
echo.
echo [*] Thực hiện quy trình xây dựng đầy đủ...
call :clean
call :test
call :build
echo [✓] Quy trình xây dựng đầy đủ hoàn tất!
pause
exit /b 0

:release
echo.
echo [*] Chuẩn bị cho phát hành...
echo.
echo Danh sách kiểm tra:
echo   [ ] Cập nhật pyproject.toml - version
echo   [ ] Cập nhật docs/changelog.md
echo   [ ] Chạy tất cả kiểm tra (build.cmd full)
echo   [ ] Tạo git tag (git tag -a vX.X.X -m "Release...")
echo   [ ] Đẩy tag (git push origin vX.X.X)
echo.
echo Tải lên PyPI:
echo   Bước 1: Kiểm tra gói
twine check dist\*
echo.
echo   Bước 2: Tải lên Test PyPI (tuỳ chọn)
echo   twine upload --repository testpypi dist/*
echo.
echo   Bước 3: Tải lên PyPI chính thức
echo   twine upload dist/*
echo.
echo   Bước 4: Tạo GitHub Release
echo   https://github.com/mrtinhnguyen/NotebookLM2PPT/releases/new
echo.
pause
exit /b 0

:error
echo.
echo [✗] Lỗi! Quy trình bị dừng.
pause
exit /b 1
