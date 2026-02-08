import win32api

# Lấy kích thước màn hình
screen_width = win32api.GetSystemMetrics(0)
screen_height = win32api.GetSystemMetrics(1)

def get_effective_top_left(top_left, width, height):
    """
    Tính toán tọa độ góc trên bên trái (top_left) thực tế.
    Nếu ảnh/khu vực đã chiếm đầy hoặc vượt quá màn hình, hoặc cài đặt offset khiến nó vượt ra ngoài màn hình thì sẽ được điều chỉnh.
    """
    effective_top_left = list(top_left)
    
    # Nếu chiều rộng đã lấp đầy hoặc vượt quá chiều rộng màn hình, thì độ lệch ngang sẽ không hoạt động.
    if width >= screen_width:
        effective_top_left[0] = 0
    # Việc điều chỉnh độ lệch dọc sẽ thất bại nếu chiều cao đã lấp đầy hoặc vượt quá chiều cao màn hình.
    if height >= screen_height:
        effective_top_left[1] = 0
    
    # Kiểm tra giới hạn: Đảm bảo khu vực không vượt quá phía bên phải và phía dưới màn hình.
    if effective_top_left[0] + width > screen_width:
        effective_top_left[0] = max(0, screen_width - width)
    if effective_top_left[1] + height > screen_height:
        effective_top_left[1] = max(0, screen_height - height)
        
    return tuple(effective_top_left)
