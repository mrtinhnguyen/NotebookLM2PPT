import numpy as np
from scipy.interpolate import griddata

def inpaint_manual(img, mask, fill_color=(255, 255, 255), max_iter=20):
    """
    Hàm xóa watermark bằng cách chỉ định màu thủ công

    Tham số:
        img: dữ liệu ảnh (H, W, 3)
        mask: mặt nạ (H, W)
        fill_color: màu muốn điền vào, tuple hoặc list, ví dụ (255, 255, 255).
                    Lưu ý: nếu dùng `cv2.imread`, thứ tự là (B, G, R).
                    Nếu dùng PIL hoặc matplotlib, thứ tự là (R, G, B).
        max_iter: số lần làm mượt mép. 0 nghĩa là chỉ điền, không làm mượt;
                  khuyến nghị 10-20 để loại bỏ răng cưa.
    """
    # 1. Tiền xử lý định dạng
    img_float = img.astype(np.float32)
    
    # Đảm bảo `mask` là ma trận 2D
    if mask.ndim == 3: mask = mask[:, :, 0]
    mask = mask > 100 # Nhị phân hóa
    
    # 【Bước A】 Phóng to Mask
    # Bước này không thể bỏ: nếu bỏ, các pixel xám ở mép chữ sẽ còn lại,
    # tạo ra một vòng outline bẩn.
    # mask_dilated = simple_dilate(mask, iterations=3)
    mask_dilated = mask
    
    # 2. Tối ưu hiệu năng: trích ROI (chỉ xử lý vùng thuộc Mask)
    rows, cols = np.where(mask_dilated)
    if len(rows) == 0: return img
    
    pad = 2
    y1, y2 = max(0, rows.min()-pad), min(img.shape[0], rows.max()+pad+1)
    x1, x2 = max(0, cols.min()-pad), min(img.shape[1], cols.max()+pad+1)
    
    img_crop = img_float[y1:y2, x1:x2]
    mask_crop = mask_dilated[y1:y2, x1:x2]
    
    # --- 【Bước B】 Điền màu trực tiếp ---
    # Chuyển `fill_color` thành numpy array để tiện broadcast
    color_val = np.array(fill_color, dtype=np.float32)
    
    # Gán trực tiếp: watermark gốc sẽ bị ghi đè bởi màu này.
    # `img_crop[mask_crop]` chọn các pixel (N, 3); gán một (3,) sẽ tự động broadcast.
    img_crop[mask_crop] = color_val
    
    # --- 【Bước C】 Feather mép (tùy chọn) ---
    # Nếu `max_iter > 0`, ta làm cho màu đã điền hòa nhẹ với xung quanh
    # để giảm cảm giác 'cắt' ở mép.
    if max_iter > 0:
        mask_3d = mask_crop[:, :, np.newaxis]
        for i in range(max_iter):
            # Laplacian smoothing
            neighbor_sum = (
                img_crop[:-2, 1:-1] + 
                img_crop[2:,  1:-1] + 
                img_crop[1:-1, :-2] + 
                img_crop[1:-1, 2:]
            )
            avg = neighbor_sum / 4.0
            
            center_view = img_crop[1:-1, 1:-1]
            roi_mask = mask_3d[1:-1, 1:-1]
            
            # Cập nhật màu cho vùng trung tâm
            np.copyto(center_view, avg, where=roi_mask)

    # 3. Gán trả giá trị đã xử lý về ảnh gốc
    img_float[y1:y2, x1:x2] = img_crop
    
    return np.clip(img_float, 0, 255).astype(np.uint8)


def inpaint_numpy_onion(img, mask):
    """
    Thuần NumPy cài đặt thuật toán sửa từ ngoài vào trong (Onion-Peel) tương tự Telea.
    Nguyên lý chính: mỗi lần chỉ sửa vòng mép ngoài cùng của mask, tham chiếu các pixel đã biết xung quanh,
    sau khi sửa xong vòng này nó sẽ trở thành pixel đã biết, tiếp tục sửa vòng tiếp theo.
    Cách này giúp kéo dài các đường và gradient của nền vào bên trong thay vì làm nhoè.
    """
    # 1. Tiền xử lý
    # Chuyển về float để thuận tiện cho các phép toán
    img = img.astype(np.float32)
    
    # Đảm bảo mask là ma trận 0/1 (0=background, 1=watermark)
    if mask.ndim == 3: mask = mask[:, :, 0]
    mask = (mask > 100).astype(np.uint8)
    
    # Trích ROI (chỉ xử lý vùng quanh watermark để tăng tốc)
    rows, cols = np.where(mask)
    if len(rows) == 0: return img.astype(np.uint8)
    
    pad = 2
    y1, y2 = max(0, rows.min()-pad), min(img.shape[0], rows.max()+pad+1)
    x1, x2 = max(0, cols.min()-pad), min(img.shape[1], cols.max()+pad+1)
    
    img_crop = img[y1:y2, x1:x2]
    mask_crop = mask[y1:y2, x1:x2]
    
    # remaining_mask lưu vùng còn cần sửa; ban đầu bằng mask_crop
    remaining_mask = mask_crop.copy()
    
    # 2. Vòng chính: cứ còn vùng chưa sửa thì tiếp tục 'lột hành'
    # Để tránh vòng lặp vô hạn (ví dụ đảo cô lập), đặt số bước tối đa
    max_steps = max(img_crop.shape) 
    
    # Định nghĩa offsets cho vùng lân cận 3x3
    offsets = [
        (-1, -1), (-1, 0), (-1, 1),
        ( 0, -1),          ( 0, 1),
        ( 1, -1), ( 1, 0), ( 1, 1)
    ]
    
    for step in range(max_steps):
        # Nếu đã sửa xong hết thì thoát
        if np.sum(remaining_mask) == 0:
            break
            
        # --- A. Tìm 'lớp mép' hiện tại ---
        # --- A. Tìm 'lớp mép' hiện tại ---
        # Logic: pixel cần sửa (1), nhưng có ít nhất 1 neighbor là đã biết (0)
        # Có thể dùng erosion (morphology) để tính: edge = Mask - eroded(Mask)
        
        # Thực hiện erosion đơn giản bằng numpy (Erosion)
        # Nếu tất cả neighbor đều là 1 thì center là 1; nếu có 1 neighbor là 0 thì center trở 0
        # Nhờ đó lớp mép sẽ được tách ra, phần core là nội tâm
        
        # Dùng slicing để nhanh kiểm tra liệu vùng lân cận có toàn 1 hay không
        eroded = remaining_mask.copy()
        # Chỉ cần một hướng là 0 thì coi như bị xói mòn
        # Tức là: up & down & left & right
        up    = remaining_mask[1:]
        down  = remaining_mask[:-1]
        left  = remaining_mask[:, 1:]
        right = remaining_mask[:, :-1]
        
        # Để khớp kích thước cần pad hoặc dùng slice
        # Ở đây dùng logic đơn giản: kiểm tra core bằng các phép cắt
        
        # Cách thuần numpy: tính core rồi lấy border = mask & ~core
        is_border = np.zeros_like(remaining_mask, dtype=bool)
        
        # Chuẩn bị known_mask: 0=chưa sửa, 1=đã biết
        known_mask = 1 - remaining_mask
        
        # Hoặc cách trực tiếp hơn:
        # border = Mask & (~eroded(Mask))
        # Ở đây ta tự thực hiện erosion bằng các phép cắt
        m_pad = np.pad(remaining_mask, 1, mode='constant', constant_values=1)
        # Kiểm tra trên/dưới/trái/phải; nếu tất cả là 1 thì giữ là lõi, ngược lại là mép
        sub_up    = m_pad[:-2, 1:-1]
        sub_down  = m_pad[2:,  1:-1]
        sub_left  = m_pad[1:-1, :-2]
        sub_right = m_pad[1:-1, 2:]
        
        core = remaining_mask & sub_up & sub_down & sub_left & sub_right
        border_mask = remaining_mask & (~core)
        
        # Nếu không tìm được bất kỳ border nào trong vòng này (ví dụ toàn đảo nhỏ),
        # dùng biện pháp cuối cùng: điền giá trị trung bình của các pixel đã biết
        if np.sum(border_mask) == 0:
            pass_mask = remaining_mask.astype(bool)
            if np.sum(pass_mask) > 0:
                valid_pixels = img_crop[~remaining_mask.astype(bool)]
                if len(valid_pixels) > 0:
                    fill_val = np.mean(valid_pixels, axis=0)
                else:
                    fill_val = np.array([255, 255, 255])
                img_crop[pass_mask] = fill_val
            break
            
        # --- B. Sửa lớp mép ---
        # --- B. Sửa lớp mép ---
        # Với mỗi pixel trong border_mask, tính trung bình (có thể coi là có trọng số)
        # của các pixel "đã biết" xung quanh
        
        # Lấy toạ độ pixel nằm trong border
        border_y, border_x = np.where(border_mask)
        
        # Để nhanh, không dùng trọng số phức tạp; chỉ tính trung bình của neighbor đã biết
        # Phải vectorize để có hiệu năng chấp nhận được
        
        # Bộ cộng (accumulator)
        sum_color = np.zeros((len(border_y), 3), dtype=np.float32)
        count_valid = np.zeros((len(border_y), 1), dtype=np.float32)
        
        for dy, dx in offsets:
            ny, nx = border_y + dy, border_x + dx
            
            # Kiểm tra vượt biên
            valid_idx = (ny >= 0) & (ny < img_crop.shape[0]) & \
                        (nx >= 0) & (nx < img_crop.shape[1])
            
            # Chỉ xử lý các index hợp lệ
            # và neighbor phải là pixel đã biết (remaining_mask[ny, nx] == 0)
            
            # Việc index phức tạp, chuyển sang phép toán toàn cục (tương tự convolution)
            pass
        
        # === Phương án vector hóa đơn giản thay thế ===
        # Vòng lặp phía trên khó viết; ta dùng thao tác dịch toàn ảnh
        # 1. Chuẩn bị Known Mask
        known = (1 - remaining_mask).astype(np.float32)
        known_3d = known[:, :, np.newaxis]
        
        # 2. Chuẩn bị Image * Known
        img_known = img_crop * known_3d
        
        # 3. Tính tổng màu trong vùng lân cận (Color) và đếm lân cận (Weight)
        # Thực hiện thủ công phép chập 3x3 (tổng)
        total_color = np.zeros_like(img_crop)
        total_weight = np.zeros_like(known_3d)
        
        for dy, dx in offsets:
            # Cắt lát sau khi dịch (shifted slices)
            # src: [1:-1] based logic
            # Dùng padding sẽ đơn giản hơn
            img_pad = np.pad(img_known, ((1,1),(1,1),(0,0)), 'constant')
            w_pad   = np.pad(known_3d,  ((1,1),(1,1),(0,0)), 'constant')
            
            # Ví dụ dy=-1, dx=-1 tương đương lấy pixel phải-dưới để điền cho trái-trên
            # Miền cắt tương ứng là [0:-2, 0:-2]
            # Để tổng quát, ta dùng slice trực tiếp
            
            sy_start, sy_end = 1+dy, img_pad.shape[0]-1+dy
            sx_start, sx_end = 1+dx, img_pad.shape[1]-1+dx
            
            shifted_img = img_pad[sy_start:sy_end, sx_start:sx_end]
            shifted_w   = w_pad[sy_start:sy_end, sx_start:sx_end]
            
            total_color += shifted_img
            total_weight += shifted_w
            
        # 4. Tính giá trị trung bình
        # Tránh chia cho 0
        total_weight[total_weight == 0] = 1.0 
        avg_color = total_color / total_weight
        
        # 5. Chỉ cập nhật vùng border_mask
        # Lưu ý: ở đây chỉ gán avg_color vào border_mask
        border_bool = border_mask.astype(bool)
        img_crop[border_bool] = avg_color[border_bool]
        
        # --- C. Cập nhật Mask (lột bớt một lớp) ---
        # Vòng này đã sửa xong, biến thành 'đã biết' cho vòng tiếp theo
        remaining_mask[border_bool] = 0

    # 3. Trả lại vào ảnh gốc
    # Nhớ chuyển về uint8
    img[y1:y2, x1:x2] = img_crop
    
    return np.clip(img, 0, 255).astype(np.uint8)




def inpaint_scipy_griddata(img, mask):
    """
    Sử dụng SciPy `griddata` để nội suy điền vùng bị che phủ.
    Đây là phương pháp toán học gần nhất để loại bỏ watermark nền đơn giản.
    Nó sẽ phù hợp một bề mặt từ các pixel xung quanh để lấp các vùng thiếu.
    """
    # Tiền xử lý
    if mask.ndim == 3: mask = mask[:,:,0]
    mask = mask > 0
    
    # Lưới tọa độ
    h, w = img.shape[:2]
    y, x = np.mgrid[0:h, 0:w]
    
    # 1. Tìm tất cả toạ độ và màu của các pixel 'đã biết' (background)
    # Để nhanh, chỉ lấy phần background gần vùng mask (không dùng toàn bộ ảnh)
    # Ở đây đơn giản ta lấy phủ định của mask
    known_mask = ~mask
    
    # Tối ưu: chỉ lấy ROI, nếu không tính toàn ảnh sẽ rất chậm
    rows, cols = np.where(mask)
    if len(rows) == 0: return img
    pad = 5
    y_min, y_max = max(0, rows.min()-pad), min(h, rows.max()+pad)
    x_min, x_max = max(0, cols.min()-pad), min(w, cols.max()+pad)
    
    # Cắt (slice)
    img_roi = img[y_min:y_max, x_min:x_max]
    mask_roi = mask[y_min:y_max, x_min:x_max]
    
    # Chuẩn bị điểm dữ liệu
    # points: toạ độ của pixel đã biết (N, 2)
    # values: màu của pixel đã biết (N, 3)
    known_y, known_x = np.where(~mask_roi)
    target_y, target_x = np.where(mask_roi)
    
    # Nếu có quá nhiều điểm background, ta lấy mẫu ngẫu nhiên để tăng tốc (griddata O(N log N))
    if len(known_y) > 2000:
        idx = np.random.choice(len(known_y), 2000, replace=False)
        points = np.column_stack((known_y[idx], known_x[idx]))
        values = img_roi[known_y[idx], known_x[idx]]
    else:
        points = np.column_stack((known_y, known_x))
        values = img_roi[known_y, known_x]
        
    xi = np.column_stack((target_y, target_x))
    
    # 2. Bước chính: nội suy
    # method='linear' nhanh và cho chuyển tiếp hợp lý
    # method='cubic' mượt hơn nhưng chậm và có thể tạo artefact ở mép
    interpolated = griddata(points, values, xi, method='linear')
    
    # 3. Gán lại vào ảnh
    img_roi[target_y, target_x] = interpolated
    img[y_min:y_max, x_min:x_max] = img_roi
    
    return img