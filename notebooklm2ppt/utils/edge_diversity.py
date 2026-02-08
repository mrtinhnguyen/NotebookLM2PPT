import numpy as np

def compute_edge_diversity_numpy(image_cv, left, top, right, bottom, tolerance=15):
    """
    Sử dụng Numpy để thay thế DBSCAN để tính toán tính nhất quán về màu sắc của cạnh.
    tolerance: Dung sai, tương tự như eps của DBSCAN. Giá trị càng lớn, càng bỏ qua các khác biệt màu nhỏ.
    """
    left, top, right, bottom = round(left), round(top), round(right), round(bottom)
    
    # Kiểm tra giới hạn, ngăn chặn việc lập chỉ mục vượt quá giới hạn
    h, w, _ = image_cv.shape
    left = max(0, left); top = max(0, top)
    right = min(w, right); bottom = min(h, bottom)

    # Trích xuất các pixel cạnh
    top_edge = image_cv[top:top+1, left:right]      # Lưu ý: top-1 có thể vượt quá giới hạn, thay bằng top
    bottom_edge = image_cv[bottom-1:bottom, left:right] 
    left_edge = image_cv[top:bottom, left:left+1]
    right_edge = image_cv[top:bottom, right-1:right]
    
    edges = [top_edge, bottom_edge, left_edge, right_edge]
    
    # Lọc ra các lát cắt trống (ngăn chặn tọa độ trùng nhau gây sự cố)
    valid_edges = [e.reshape(-1, 3) for e in edges if e.size > 0]
    if not valid_edges:
        return 1.0, np.array([255, 255, 255]) # Mặc định trả về đa dạng cao (không điền), trắng

    flatten_points = np.concatenate(valid_edges, axis=0)

    if flatten_points.shape[0] == 0:
         return 1.0, np.array([255, 255, 255])

    # --- Cách thay thế lôgic cốt lõi DBSCAN ---
    
    # 1. Lượng tử hóa màu (chia hết cho tolerance), tương đương với việc nhóm các màu tương tự vào xô
    quantized_points = flatten_points // tolerance
    
    # 2. Thống kê các màu duy nhất và số lượng
    unique_colors, counts = np.unique(quantized_points, axis=0, return_counts=True)
    
    # 3. Tìm màu có tỷ lệ chiếm đứng cao nhất
    max_count_index = np.argmax(counts)
    max_count = counts[max_count_index]
    total_count = np.sum(counts)
    
    main_ratio = max_count / total_count
    
    # 4. Nhận màu trung bình trong "xô" này (hoặc trực tiếp hoàn nguyên màu lượng tử hóa)
    # Để chính xác, chúng ta có thể lấy giá trị trung bình của tất cả pixel gốc thuộc xô này
    dominant_quantized_color = unique_colors[max_count_index]
    # Tạo mặt nạ để tìm pixel gốc
    mask = np.all((flatten_points // tolerance) == dominant_quantized_color, axis=1)
    main_color = np.mean(flatten_points[mask], axis=0)
    main_color = main_color.astype(np.uint8).tolist()

    return 1 - main_ratio, main_color

def compute_edge_average_color(image_cv, left, top, right, bottom):
    """
    Tính toán màu trung bình của cạnh.
    """
    left, top, right, bottom = round(left), round(top), round(right), round(bottom)
    
    h, w, _ = image_cv.shape
    left = max(0, left); top = max(0, top)
    right = min(w, right); bottom = min(h, bottom)

    top_edge = image_cv[top:top+1, left:right]
    bottom_edge = image_cv[bottom-1:bottom, left:right]
    left_edge = image_cv[top:bottom, left:left+1]
    right_edge = image_cv[top:bottom, right-1:right]
    
    edges = [top_edge, bottom_edge, left_edge, right_edge]
    valid_edges = [e.reshape(-1, 3) for e in edges if e.size > 0]
    
    if not valid_edges:
        return np.array([255, 255, 255])

    flatten_points = np.concatenate(valid_edges, axis=0)
    average_color = np.mean(flatten_points, axis=0)
    average_color = average_color.astype(np.uint8).tolist()

    return average_color
