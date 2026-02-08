"""
Định nghĩa các hằng số cấu hình mặc định thống nhất
"""

# Cài đặt mặc định nhà máy xử lý tác vụ (chỉ sử dụng lần đầu tiên)
DEFAULT_TASK_SETTINGS = {
    "dpi": 150,
    "ratio": 0.8,
    "inpaint": True,
    "inpaint_method": "background_smooth",  # Cần điều chỉnh dựa trên phương pháp cụ thể
    "image_only": False,
    "force_regenerate": False,
    "unify_font": True,
    "font_name": "Calibri",
    "page_range": ""
}

# Giá trị mặc định nhà máy cho các cài đặt liên quan đến tự động hóa
DEFAULT_AUTOMATION_SETTINGS = {
    "delay": 0,  # Thời gian chờ (giây)
    "timeout": 50,  # Thời gian chờ (giây)
    "done_offset": "",  # Độ lệch nút
    "calibrate": True  # Tự động hiệu chuẩn
}

# Giá trị mặc định liên quan đến GUI
DEFAULT_GUI_VALUES = {
    "output_dir": "workspace",
    "language": "vi"
}

# Lấy cài đặt mặc định hoàn chỉnh sau khi hợp nhất (xem xét cài đặt lần trước của người dùng)
def get_default_settings(output_dir="workspace", inpaint_method="background_smooth", user_last_settings=None):
    """
    Lấy cài đặt mặc định tác vụ hoàn chỉnh, ưu tiên sử dụng cài đặt của người dùng lần trước
    
    Args:
        output_dir: Thư mục đầu ra
        inpaint_method: Phương pháp sửa chữa (sẽ lấy cái đầu tiên từ phương pháp dịch tại thời gian chạy)
        user_last_settings: Cài đặt được sử dụng lần trước của người dùng (đọc từ config.json)
    
    Returns:
        dict: Từ điển cài đặt hoàn chỉnh
    """
    # Trước tiên sử dụng giá trị mặc định nhà máy
    settings = DEFAULT_TASK_SETTINGS.copy()
    
    # Nếu có cài đặt lần trước của người dùng, hãy ghi đè giá trị mặc định
    if user_last_settings:
        settings.update(user_last_settings)
    
    # Luôn sử dụng thư mục đầu ra hiện tại
    settings["output_dir"] = output_dir
    
    # Chỉ sử dụng phương pháp mặc định được truyền vào khi người dùng lần trước không lưu phương pháp sửa chữa
    if not user_last_settings or 'inpaint_method' not in user_last_settings:
        settings["inpaint_method"] = inpaint_method
    
    return settings

