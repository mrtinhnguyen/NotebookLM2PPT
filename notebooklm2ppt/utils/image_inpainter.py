# from pyinpaint import Inpaint
import numpy as np
from skimage.restoration import inpaint
from PIL import Image
from .edge_diversity import compute_edge_diversity_numpy, compute_edge_average_color
import math
from .inpaint_methods import inpaint_manual, inpaint_numpy_onion, inpaint_scipy_griddata


INPAINT_METHODS = [
    {
        'id': 'background_smooth',
        'name': 'Làm mịn thông minh (Khuyến nghị)',  # Bỏ "màu nền", nhấn mạnh thông minh
        'description': 'Hiệu quả tổng thể tốt nhất, thích hợp cho hầu hết các trường hợp xóa văn bản và hình mờ'
    },
    {
        'id': 'edge_mean_smooth',
        'name': 'Điền trung bình cạnh',
        'description': 'Điền trung bình màu sắc của các pixel xung quanh, phù hợp với nền đơn sắc hoặc đơn giản'
    },
    {
        'id': 'background',
        'name': 'Điền màu đơn sắc cực nhanh',
        'description': 'Điền trực tiếp một màu nền duy nhất, chỉ phù hợp với nền siêu đơn giản, tốc độ nhanh nhất'
    },
    {
        'id': 'onion',
        'name': 'Sửa chữa từng lớp từ bên ngoài vào trong', # Giải thích nguyên tắc "vỏ hành"
        'description': 'Sửa chữa từng lớp từ bên ngoài vào trong, thích hợp cho các vết cước dài hoặc sửa chữa dòng'
    },
    {
        'id': 'griddata',
        'name': 'Nội suy quá trình chuyển tiếp gradient', # Giải thích hiệu quả "nội suy lưới"
        'description': 'Tính toán quá trình chuyển tiếp bề mặt mịn, phù hợp với nền có gradient'
    },
    {
        'id': 'skimage',
        'name': 'Sửa chữa Biharmonic quang ảnh', # Cho tên cao cấp cho Biharmonic
        'description': 'Lượng tính toán lớn, tốc độ chậm, nhưng giữ tính liên tục quang ảnh tốt hơn'
    },
]

METHOD_ID_TO_NAME = {m['id']: m['name'] for m in INPAINT_METHODS}
METHOD_NAME_TO_ID = {m['name']: m['id'] for m in INPAINT_METHODS}


def get_method_names():
    """Lấy danh sách tên phương pháp Việt Nam, sử dụng cho hộp thả xuống GUI"""
    return [m['name'] for m in INPAINT_METHODS]


def get_method_id(method_name_or_id):
    """Chuyển đổi tên phương pháp hoặc ID thành ID chuẩn"""
    if method_name_or_id in METHOD_ID_TO_NAME:
        return method_name_or_id
    return METHOD_NAME_TO_ID.get(method_name_or_id, 'background_smooth')


def get_method_name_from_id(method_id):
    """Chuyển đổi ID thành tên Việt"""
    return METHOD_ID_TO_NAME.get(method_id, get_method_names()[0])


def inpaint_image(image_path, output_path, inpaint_method='skimage'):
    inpaint_method = get_method_id(inpaint_method)
    
    image = Image.open(image_path)
    image_defect = np.array(image)
    
    
    # [{\"width\":240,\"top\":1530,\"height\":65,\"left\":2620}]
    r1,r2,c1,c2 = 1536,1598,2627,2863

    old_width, old_height = 2867,1600

    image_width, image_height = image_defect.shape[1], image_defect.shape[0]
    ratio = image_width / old_width

    assert abs(ratio - (image_height / old_height)) < 0.01, "Tỷ lệ hình ảnh không đúng, không thể sửa chữa"

    r1 = math.floor(r1 * ratio)
    r2 = math.ceil(r2 * ratio)
    c1 = math.floor(c1 * ratio)
    c2 = math.ceil(c2 * ratio)
    if inpaint_method =='skimage':
        dtype = bool
        fill_val = True
    else:
        dtype = np.uint8
        fill_val = 255

    mask = np.zeros(image_defect.shape[:-1], dtype=dtype)
    mask[r1:r2, c1:c2] = fill_val

    edge_diversity, fill_color = compute_edge_diversity_numpy(image_defect, c1, r1, c2, r2)

    if edge_diversity < 0.1 or inpaint_method == 'background': # Điền trực tiếp xong, tốc độ nhanh nhất
        print("Điền trực tiếp",edge_diversity, fill_color)
        image_defect[r1:r2, c1:c2] = fill_color
        image_result = image_defect
    elif inpaint_method == 'skimage': # Tốc độ chậm nhất, hiệu quả cũng trung bình
        image_result = inpaint.inpaint_biharmonic(image_defect, mask, channel_axis=-1)
        image_result = (image_result*255).astype("uint8")
    elif inpaint_method == 'onion':  # Hiệu quả trung bình, hiệu quả cũng ổn
        image_result = inpaint_numpy_onion(image_defect, mask)
    elif inpaint_method == 'griddata': # Tương tự như onion
        image_result = inpaint_scipy_griddata(image_defect, mask)
    elif inpaint_method == 'background_smooth': # Tốc độ thứ hai nhanh, cũng trơn
        image_result = inpaint_manual(image_defect, mask, fill_color, max_iter=100)
    elif inpaint_method == 'edge_mean_smooth':
        fill_color = compute_edge_average_color(image_defect, c1, r1, c2, r2)
        image_result = inpaint_manual(image_defect, mask, fill_color, max_iter=100)
    else:
        raise ValueError(f"Unknown inpaint method: {inpaint_method}")


    Image.fromarray(image_result).save(output_path)
