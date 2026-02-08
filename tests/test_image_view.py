import sys
from PIL import Image, ImageTk

# Nhập tkinter tương thích với phiên bản Python
if sys.version_info[0] == 2:
    import Tkinter as tkinter
else:
    import tkinter

def showPIL(pilImage):
    root = tkinter.Tk()
    
    # 1. Nhận độ phân giải màn hình
    w, h = root.winfo_screenwidth(), root.winfo_screenheight()
    
    # 2. Đặt toàn màn hình không viền
    root.attributes('-fullscreen', True)
    root.configure(background='black')
    root.focus_set()
    
    # 3. Liên kết sự kiện thoát: Nhấn phím Esc trên bàn phím để đóng cửa sổ
    root.bind("<Escape>", lambda e: (e.widget.withdraw(), e.widget.quit()))
    
    # 4. Tạo canvas và điền nền thành màu đen, loại bỏ tất cả các viền
    canvas = tkinter.Canvas(root, width=w, height=h,
                           highlightthickness=0, borderwidth=0)
    canvas.pack(fill='both', expand=True)
    canvas.configure(background='black')
    
    # 5. Điều chỉnh kích thước hình ảnh để phù hợp với màn hình (giữ tỷ lệ khung hình)
    imgWidth, imgHeight = pilImage.size
    if imgWidth > w or imgHeight > h:
        ratio = min(w / float(imgWidth), h / float(imgHeight))
        imgWidth = int(imgWidth * ratio)
        imgHeight = int(imgHeight * ratio)
        # Lưu ý: Image.ANTIALIAS có thể được thay đổi thành Image.LANCZOS trong phiên bản Pillow mới
        pilImage = pilImage.resize((imgWidth, imgHeight), Image.LANCZOS)
    
    # 6. Chuyển đổi hình ảnh PIL thành đối tượng hình ảnh Tkinter
    image = ImageTk.PhotoImage(pilImage)
    
    # 7. Hiển thị hình ảnh ở giữa canvas
    imagesprite = canvas.create_image(w / 2, h / 2, image=image)
    
    root.mainloop()

# Ví dụ sử dụng
if __name__ == "__main__":
    # Vui lòng thay thế "your_image.png" bằng đường dẫn hình ảnh cục bộ của bạn
    try:
        pilImage = Image.open(r"C:\Users\TonyX\Desktop\Demo.jpg")
        showPIL(pilImage)
    except FileNotFoundError:
        print("Không tìm thấy tệp hình ảnh, vui lòng kiểm tra đường dẫn.")