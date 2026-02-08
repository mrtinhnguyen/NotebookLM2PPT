"""Tạo PPT trực tiếp từ JSON của PaddleOCR (PP-Structure)"""

import os
import json
import argparse
import copy
from pathlib import Path
import numpy as np
from PIL import Image
from notebooklm2ppt.pdf2png import pdf_to_png
from notebooklm2ppt.utils.ppt_combiner import clean_ppt
from notebooklm2ppt.utils.edge_diversity import compute_edge_diversity_numpy
from spire.presentation import *
from spire.presentation.common import *

# ============================================================================
# Hàm trợ giúp phân tích văn bản
# ============================================================================


def calculate_font_size(height,
                        min_font_size=8,
                        is_multiline=False,
                        line_count=1):
    """
    Tính kích thước font phù hợp dựa trên kích thước hộp văn bản và nội dung
    
    Args:
        height: chiều cao hộp văn bản
        min_font_size: kích thước font nhỏ nhất
        is_multiline: có phải nhiều dòng không
        line_count: số dòng
        
    Returns:
        int: kích thước font ước lượng
    """
    if is_multiline and line_count > 1:
        line_height = height / line_count
        font_size = line_height * 0.75
    else:
        font_size = height * 0.75

    font_size = max(min_font_size, int(font_size))
    return font_size


def get_line_count(block_bbox, ocr_boxes):
    """
    Tính số dòng thực tế trong một khối văn bản
    
    Args:
        block_bbox: bbox của khối [x1, y1, x2, y2]
        ocr_boxes: danh sách hộp OCR
        
    Returns:
        int: số dòng ước tính
    """
    bx1, by1, bx2, by2 = block_bbox

    # Lọc các hộp OCR nằm trong phạm vi block (dựa trên tâm)
    contained_boxes = []
    for obox in ocr_boxes:
        ox1, oy1, ox2, oy2 = obox
        cx = (ox1 + ox2) / 2
        cy = (oy1 + oy2) / 2

        if bx1 <= cx <= bx2 and by1 <= cy <= by2:
            contained_boxes.append(obox)

    if not contained_boxes:
        return 0

    # Sắp xếp theo tâm Y và dùng phân cụm đơn giản để ước lượng số dòng
    contained_boxes.sort(key=lambda b: (b[1] + b[3]) / 2)

    line_count = 1
    last_y_center = (contained_boxes[0][1] + contained_boxes[0][3]) / 2
    last_h = contained_boxes[0][3] - contained_boxes[0][1]

    for j in range(1, len(contained_boxes)):
        curr_y_center = (contained_boxes[j][1] + contained_boxes[j][3]) / 2
        curr_h = contained_boxes[j][3] - contained_boxes[j][1]

        # Ngưỡng: nếu khoảng cách dọc lớn hơn 60% so với chiều cao dòng thì coi là dòng mới
        if abs(curr_y_center - last_y_center) > max(last_h, curr_h) * 0.6:
            line_count += 1
            last_y_center = curr_y_center
            last_h = curr_h

    return line_count


# ============================================================================
# Hàm cấu hình PPT
# ============================================================================


def setup_presentation(pdf_size):
    """
    Tạo và cấu hình PPT theo kích thước PDF
    
    Args:
        pdf_size: tuple (width, height) của PDF
        
    Returns:
        tuple: (presentation, ppt_width, ppt_height)
    """
    presentation = Presentation()
    if presentation.Slides.Count > 0:
        presentation.Slides.RemoveAt(0)

    pdf_width, pdf_height = pdf_size
    pdf_ratio = pdf_width / pdf_height
    strategy = "diff"
    if strategy == "diff":
        # Căn theo tỉ lệ khung để thiết lập kích thước PPT
        if pdf_ratio > 1.65:
            presentation.SlideSize.Type = SlideSizeType.Screen16x9
        elif pdf_ratio > 1.45:
            presentation.SlideSize.Type = SlideSizeType.Screen16x10
        elif pdf_ratio > 1.0:
            presentation.SlideSize.Type = SlideSizeType.Screen4x3
        else:
            ppt_height = 720
            ppt_width = ppt_height * pdf_ratio
            presentation.SlideSize.Type = SlideSizeType.Custom
            presentation.SlideSize.Size = SizeF(float(ppt_width),
                                                float(ppt_height))
    else:
        presentation.SlideSize.Type = SlideSizeType.Custom
        presentation.SlideSize.Size = SizeF(float(pdf_width),
                                            float(pdf_height))

    ppt_width = presentation.SlideSize.Size.Width
    ppt_height = presentation.SlideSize.Size.Height
    print(f"PPT Size: {ppt_width} x {ppt_height}")

    return presentation, ppt_width, ppt_height


# ============================================================================
# Hàm xử lý khối văn bản
# ============================================================================


def should_skip_text_block(label, content):
    """
    Kiểm tra xem có nên bỏ qua khối văn bản này hay không
    
    Args:
        label: nhãn khối
        content: nội dung văn bản
        
    Returns:
        bool: True = bỏ qua, False = xử lý
    """
    # Chỉ xử lý các nhãn văn bản được quan tâm
    valid_labels = [
        'text', 'title', 'header', 'footer', 'reference', 'paragraph_title',
        'algorithm'
    ]
    if label not in valid_labels:
        return True

    # Bỏ qua watermark trong phần chân trang
    if label == 'footer' and "notebooklm" in content.lower():
        return True

    # Bỏ qua nội dung rỗng
    if not content.strip():
        return True

    return False


def create_text_shape(slide,
                      content,
                      label,
                      bbox,
                      scale,
                      ppt_width,
                      ppt_height,
                      font_size,
                      font_name,
                      delta_y=2):
    """
    Tạo shape văn bản trên slide
    
    Args:
        slide: đối tượng slide
        content: nội dung văn bản
        label: nhãn khối
        bbox: hộp [x1, y1, x2, y2]
        scale: tỉ lệ scale
        ppt_width: chiều rộng PPT
        ppt_height: chiều cao PPT
        font_size: kích thước font
        font_name: tên font
        delta_y: bù trên trục Y
        
    Returns:
        object: shape văn bản
    """
    bx1, by1, bx2, by2 = bbox

    # Chuyển toạ độ (áp dụng dịch căn chỉnh delta_y)
    left = bx1 * scale
    top = by1 * scale + delta_y
    right = bx2 * scale
    bottom = by2 * scale + delta_y
    width = right - left
    height = bottom - top


    if label =='paragraph_title':
        print(content)
        alignment = TextAlignmentType.Left
        h_padding = 5
        v_padding = 5
    else:
        alignment = TextAlignmentType.Center
        h_padding = 15
        v_padding = 5

    # Thêm khoảng đệm hợp lý
    rect = RectangleF.FromLTRB(max(0, left ),
                               max(0, top - v_padding),
                               min(ppt_width, right + h_padding + h_padding),
                               min(ppt_height, bottom + v_padding))

    # Tạo khung văn bản

    text_shape = slide.Shapes.AppendShape(ShapeType.Rectangle, rect)
    text_shape.Name = f"Block_{label}"
    text_shape.TextFrame.Text = content
    text_shape.TextFrame.FitTextToShape = True

    text_shape.TextFrame.MarginLeft = 0
    text_shape.TextFrame.MarginRight = 0
    text_shape.TextFrame.MarginTop = 0
    text_shape.TextFrame.MarginBottom = 0

    text_shape.Line.FillType = FillFormatType.none
    text_shape.Fill.FillType = FillFormatType.none
    
    # Cấu hình định dạng văn bản
    for paragraph in text_shape.TextFrame.Paragraphs:
        paragraph.Alignment = alignment
        for text_range in paragraph.TextRanges:
            text_range.LatinFont = TextFont(font_name)
            text_range.FontHeight = font_size
            text_range.Fill.FillType = FillFormatType.Solid
            text_range.Fill.SolidColor.Color = Color.FromArgb(255, 0, 0, 0)

    return text_shape


def process_text_blocks(slide,
                        parsing_res_list,
                        ocr_boxes,
                        scale,
                        ppt_width,
                        ppt_height,
                        font_name="Calibri"):
    """
    Xử lý tất cả khối văn bản trên trang
    
    Args:
        slide: đối tượng slide
        parsing_res_list: danh sách kết quả phân tích
        ocr_boxes: danh sách hộp OCR
        scale: tỉ lệ scale
        ppt_width: chiều rộng PPT
        ppt_height: chiều cao PPT
        font_name: tên font
    """
    for item in parsing_res_list:
        label = item.get('block_label', 'unknown')
        content = item.get('block_content', '')
        bbox = item.get('block_bbox')

        if not bbox:
            continue

        # Kiểm tra có nên bỏ qua khối văn bản này hay không
        if should_skip_text_block(label, content):
            continue

        # Tính số dòng và kích thước font
        line_count = get_line_count(bbox, ocr_boxes)
        is_multiline = line_count > 1

        bx1, by1, bx2, by2 = bbox
        width = (bx2 - bx1) * scale
        height = (by2 - by1) * scale

        font_size = calculate_font_size(height,
                                        is_multiline=is_multiline,
                                        line_count=line_count)

        # Tạo shape văn bản
        create_text_shape(slide, content, label, bbox, scale, ppt_width,
                          ppt_height, font_size, font_name)


# ============================================================================
# Hàm xử lý ảnh và nền
# ============================================================================


def expand_bbox(bbox, expand_px, size):
    """
    Mở rộng bbox theo số pixel cho trước
    
    Args:
        bbox: hộp [x1, y1, x2, y2]
        expand_px: số pixel mở rộng
        size: (width, height) của ảnh
        
    Returns:
        list: bbox đã mở rộng
    """
    width, height = size
    x1, y1, x2, y2 = bbox
    x1 = max(0, x1 - expand_px)
    y1 = max(0, y1 - expand_px)
    x2 = min(width, x2 + expand_px)
    y2 = min(height, y2 + expand_px)
    return [x1, y1, x2, y2]


def scale_bbox(bbox, s, make_int=True):
    """
    Phóng to/thu nhỏ bbox theo tỉ lệ và làm tròn
    
    Args:
        bbox: [x1, y1, x2, y2]
        s: hệ số scale
        
    Returns:
        list: bbox sau khi scale và làm tròn
    """
    if make_int:
        l, t, r, b = bbox
        # Làm tròn dưới cho góc trên-trái, làm tròn lên cho góc dưới-phải
        return [int(l * s), int(t * s), int(np.ceil(r * s)), int(np.ceil(b * s))]
    else:
        return [coord * s for coord in bbox]


def extract_foreground_element(slide, item, index, image_cv, img_scale, scale,
                               pdf_size, png_dir, page_idx):
    """
    Trích phần tử tiền cảnh (ảnh, bảng, biểu đồ) và thêm vào slide
    
    Args:
        slide: đối tượng slide
        item: thông tin phần tử
        index: chỉ số phần tử
        image_cv: mảng ảnh (numpy)
        img_scale: tỉ lệ ảnh so với PDF
        scale: tỉ lệ dùng trên PPT
        png_dir: thư mục xuất PNG
        page_idx: chỉ số trang
        
    Returns:
        bool: True nếu trích thành công
    """
    label = item.get('block_label')
    bbox = item.get('block_bbox')

    if not bbox:
        return False

    expanded_bbox = expand_bbox(bbox, expand_px=2, size=pdf_size)

    # Tọa độ trên ảnh gốc để cắt (căn chỉnh offset)
    l_img, t_img, r_img, b_img = scale_bbox(expanded_bbox, img_scale)

    if r_img <= l_img or b_img <= t_img:
        print("Vùng cắt không hợp lệ, bỏ qua")
        return False

    # Cắt và lưu
    crop = image_cv[t_img:b_img, l_img:r_img]
    crop_name = f"page_{page_idx+1}_{label}_{index}.png"
    crop_path = png_dir / crop_name
    Image.fromarray(crop).save(crop_path)

    # Thêm vào slide
    l_ppt, t_ppt, r_ppt, b_ppt = scale_bbox(expanded_bbox, scale, make_int=False)
    rect_item = RectangleF.FromLTRB(l_ppt, t_ppt, r_ppt, b_ppt)

    img_shape = slide.Shapes.AppendEmbedImageByPath(ShapeType.Rectangle,
                                                    str(crop_path), rect_item)
    img_shape.Line.FillType = FillFormatType.none
    img_shape.ZOrderPosition = 0  # Đặt ở lớp dưới cùng

    return True


def erase_region(image_cv, bbox, img_scale, pdf_size):
    """
    Xóa vùng chỉ định trên ảnh (điền màu nền)
    
    Args:
        image_cv: mảng ảnh
        bbox: hộp biên
        img_scale: tỉ lệ ảnh
        pdf_size: kích thước PDF (w, h)
        
    Returns:
        bool: True nếu xóa thành công
    """
    expanded_bbox = expand_bbox(bbox, expand_px=2, size=pdf_size)
    l, t, r, b = scale_bbox(expanded_bbox, img_scale, make_int=True)

    if r <= l or b <= t:
        print("Vùng xóa không hợp lệ, bỏ qua")
        return False

    # Tính màu tô và xóa
    _, fill_color = compute_edge_diversity_numpy(image_cv,
                                                 l,
                                                 t,
                                                 r,
                                                 b,
                                                 tolerance=20)
    image_cv[t:b, l:r] = fill_color

    return True


def process_slide_background(slide, presentation, parsing_res_list, png_file,
                             pdf_size, scale, png_dir, page_idx):
    """
    Xử lý nền slide (trích phần tử tiền cảnh, xóa vùng đã chuyển, thiết lập nền)
    
    Args:
        slide: slide
        presentation: đối tượng presentation
        parsing_res_list: danh sách kết quả phân tích
        png_file: đường dẫn PNG
        pdf_size: kích thước PDF (w, h)
        scale: tỉ lệ
        png_dir: thư mục PNG đầu ra
        page_idx: chỉ số trang
    """
    if not png_file.exists():
        return

    # Tải ảnh
    pdf_w, pdf_h = pdf_size
    img = Image.open(png_file)
    img = img.resize(pdf_size, Image.LANCZOS)
    image_cv = np.array(img)
    image_h, image_w = image_cv.shape[:2]
    img_scale = image_w / pdf_w
    ppt2img_scale = scale / img_scale

    # 1. Trích phần tử tiền cảnh (ảnh, bảng, biểu đồ)
    for i, item in enumerate(parsing_res_list):
        label = item.get('block_label')
        if label in ['image', 'table', 'chart']:
            extract_foreground_element(slide, item, i, image_cv, img_scale,
                                       scale, pdf_size, png_dir, page_idx)

    # 2. Xóa vùng đã chuyển thành textbox hoặc ảnh độc lập
    erasable_labels = [
        'text', 'title', 'header', 'footer', 'reference', 'paragraph_title',
        'image', 'table', 'algorithm', 'chart'
    ]

    for item in parsing_res_list:
        label = item.get('block_label')
        if label in erasable_labels:
            bbox = item.get('block_bbox')
            if bbox:
                erase_region(image_cv, bbox, img_scale, pdf_size)
                

    # 3. Lưu ảnh đã xử lý
    processed_png = png_dir / f"page_{page_idx+1}_paddle_processed.png"
    Image.fromarray(image_cv).save(processed_png)

    # 4. Thiết lập nền slide
    slide.SlideBackground.Type = BackgroundType.Custom
    slide.SlideBackground.Fill.FillType = FillFormatType.Picture

    stream = Stream(str(processed_png))
    image_data = presentation.Images.AppendStream(stream)
    slide.SlideBackground.Fill.PictureFill.Picture.EmbedImage = image_data
    slide.SlideBackground.Fill.PictureFill.FillType = PictureFillType.Stretch


def get_pdf_size_from_data(data):
    """
    Lấy kích thước PDF từ kết quả bố cục
    
    Args:
        data: dữ liệu JSON của PaddleOCR
        
    Returns:
        tuple: (pdf_width, pdf_height)
    """
    layout_results = data.get('layoutParsingResults', [])
    first_page_layout = layout_results[0]['prunedResult']
    pdf_w = first_page_layout['width']
    pdf_h = first_page_layout['height']
    return (pdf_w, pdf_h)

def update_data_size(data, width, height=None):
    """
    Cập nhật thông tin kích thước (width/height) trong dữ liệu
    
    Args:
        data: JSON của PaddleOCR
        width: chiều rộng mới
        height: chiều cao mới (tuỳ chọn)
        
    Returns:
        dict: dữ liệu đã cập nhật
    """
    width = int(width)
    if height is not None:
        height = int(height)
    layout_results = data.get('layoutParsingResults', [])
    
    # Cập nhật chiều rộng và cao trong kết quả bố cục
    for page_layout in layout_results:
        pruned_result = page_layout.get('prunedResult', {})
        pruned_result['width'] = width
        if height is not None:
            pruned_result['height'] = height
    
    # Cập nhật chiều rộng và cao trong dataInfo
    data_info = data.get('dataInfo', {})
    if data_info:
        data_info['width'] = width
        if height is not None:
            data_info['height'] = height
    
    # Cập nhật chiều rộng và cao trong pages
    pages_info = data_info.get('pages', [])
    if pages_info:
        for page in pages_info:
            page['width'] = width
            if height is not None:
                page['height'] = height
    
    return data

def make_data_wide_screen(data):
    """
    Chuyển dữ liệu sang tỉ lệ 16:9 (widescreen)
    
    Args:
        data: JSON của PaddleOCR
        
    Returns:
        dict: dữ liệu đã điều chỉnh
    """
    data = copy.deepcopy(data)
    
    # Lấy kích thước PDF gốc
    layout_results = data.get('layoutParsingResults', [])
    if not layout_results:
        return data
    
    first_page_layout = layout_results[0]['prunedResult']
    pdf_w = first_page_layout['width']
    pdf_h = first_page_layout['height']
    
    # Tính chiều rộng mục tiêu cho 16:9
    target_width = round(pdf_h * 16 / 9)
    
    if target_width == pdf_w:
        print(f"✓ Đã là 16:9, không cần điều chỉnh")
        return data
    
    if target_width > pdf_w:
        # Cần mở rộng chiều rộng - tính offset trái/phải
        offset_x = (target_width - pdf_w) // 2
        
        print(f"✓ Mở rộng chiều rộng: {pdf_w} -> {target_width} (dịch trái/phải mỗi bên {offset_x})")
        
        # Thiết lập chiều rộng mới
        data = update_data_size(data, target_width)
        layout_results = data.get('layoutParsingResults', [])
        for page_layout in layout_results:
            pruned_result = page_layout.get('prunedResult', {})
            parsing_res_list = pruned_result.get('parsing_res_list', [])
            for item in parsing_res_list:
                bbox = item.get('block_bbox')
                if bbox:
                    # Dịch toạ độ ngang sang phải
                    item['block_bbox'] = [bbox[0] + offset_x, bbox[1], 
                                            bbox[2] + offset_x, bbox[3]]
        
        # Điều chỉnh kết quả OCR
        ocr_results = data.get('ocrResults', [])
        for page_ocr in ocr_results:
            pruned_result = page_ocr.get('prunedResult', {})
            rec_boxes = pruned_result.get('rec_boxes', [])
            
            for bbox in rec_boxes:
                if bbox and len(bbox) >= 4:
                    # Dịch toạ độ ngang sang phải
                    bbox[0] += offset_x
                    bbox[2] += offset_x
    
    elif target_width < pdf_w:
        # Cần cắt bớt chiều rộng - tính biên trái
        left = (pdf_w - target_width) // 2
        right = left + target_width
        
        print(f"✓ Cắt chiều rộng: {pdf_w} -> {target_width} (giữ phần giữa {left}-{right})")
        
        # Thiết lập chiều rộng mới
        data = update_data_size(data, target_width)
        layout_results = data.get('layoutParsingResults', [])
        
        # Điều chỉnh tất cả tọa độ và lọc các phần tử ngoài phạm vi
        for page_layout in layout_results:
            pruned_result = page_layout.get('prunedResult', {})
            pruned_result['width'] = target_width
            
            parsing_res_list = pruned_result.get('parsing_res_list', [])
            filtered_list = []
            
            for item in parsing_res_list:
                bbox = item.get('block_bbox')
                if bbox:
                    x1, y1, x2, y2 = bbox
                    # Kiểm tra xem có trong vùng cắt không
                    if x2 > left and x1 < right:
                        # Điều chỉnh toạ độ và cắt đến biên
                        new_x1 = max(0, x1 - left)
                        new_x2 = min(target_width, x2 - left)
                        item['block_bbox'] = [new_x1, y1, new_x2, y2]
                        filtered_list.append(item)
            
            pruned_result['parsing_res_list'] = filtered_list
        
        # Điều chỉnh kết quả OCR
        ocr_results = data.get('ocrResults', [])
        for page_ocr in ocr_results:
            pruned_result = page_ocr.get('prunedResult', {})
            rec_boxes = pruned_result.get('rec_boxes', [])
            
            filtered_boxes = []
            for bbox in rec_boxes:
                if bbox and len(bbox) >= 4:
                    x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
                    # Kiểm tra xem có nằm trong phạm vi cắt hay không
                    if x2 > left and x1 < right:
                        # Điều chỉnh tọa độ
                        bbox[0] = max(0, x1 - left)
                        bbox[2] = min(target_width, x2 - left)
                        filtered_boxes.append(bbox)
            
            pruned_result['rec_boxes'] = filtered_boxes
    
    return data



def resize_data(data, pdf_size, ppt_size):
    """
    Điều chỉnh tọa độ trong dữ liệu để phù hợp với kích thước PPT
    
    Args:
        data: Dữ liệu JSON của PaddleOCR
        pdf_size: Kích thước PDF (pdf_width, pdf_height)
        ppt_size: Kích thước PPT (ppt_width, ppt_height)
        
    Returns:
        dict: Dữ liệu đã được điều chỉnh
    """
    pdf_w, pdf_h = pdf_size
    ppt_w, ppt_h = ppt_size
    
    scale_x = ppt_w / pdf_w
    scale_y = ppt_h / pdf_h
    print(f"Resize Data: scale_x={scale_x}, scale_y={scale_y}")

    assert abs(scale_x - scale_y) < 1e-2, "Tỷ lệ thu phóng X và Y không nhất quán"
    scale = scale_x
    data = copy.deepcopy(data)
    
    # Cập nhật đồng bộ thông tin kích thước trang
    data = update_data_size(data, ppt_w, ppt_h)
    
    layout_results = data.get('layoutParsingResults', [])
    ocr_results = data.get('ocrResults', [])
    
    # Điều chỉnh tọa độ trong kết quả bố cục
    for page_layout in layout_results:
        pruned_result = page_layout.get('prunedResult', {})
        parsing_res_list = pruned_result.get('parsing_res_list', [])
        
        for item in parsing_res_list:
            bbox = item.get('block_bbox')
            if bbox:
                # Điều chỉnh tọa độ khung giới hạn
                item['block_bbox'] = scale_bbox(bbox, scale, make_int=True)
    
    # Điều chỉnh tọa độ trong kết quả OCR
    for page_ocr in ocr_results:
        pruned_result = page_ocr.get('prunedResult', {})
        rec_boxes = pruned_result.get('rec_boxes', [])
        
        for bbox in rec_boxes:
            if bbox and len(bbox) >= 4:
                # Điều chỉnh tọa độ khung OCR
                new_bbox = scale_bbox(bbox, scale, make_int=True)
                bbox[0], bbox[1], bbox[2], bbox[3] = new_bbox
    
    return data



# ============================================================================
# Hàm xử lý chính
# ============================================================================


def create_ppt_from_paddle_json(json_file,
                                pdf_file,
                                output_dir,
                                out_ppt_name=None,
                                dpi=150,
                                inpaint=True,
                                inpaint_method='background_smooth'):
    """
    Tạo PPT trực tiếp từ JSON của PaddleOCR
    
    Args:
        json_file: đường dẫn file JSON của PaddleOCR
        pdf_file: đường dẫn file PDF gốc
        output_dir: thư mục đầu ra
        out_ppt_name: tên file PPT đầu ra (tuỳ chọn)
        dpi: độ phân giải ảnh khi chuyển PDF->PNG
        inpaint: có chạy inpaint hay không
        inpaint_method: phương pháp inpaint
    """
    # Xác thực tệp đầu vào
    if not os.path.exists(json_file):
        print(f"Lỗi: file JSON {json_file} không tồn tại")
        return

    if not os.path.exists(pdf_file):
        print(f"Lỗi: file PDF {pdf_file} không tồn tại")
        return

    # Chuẩn bị thư mục đầu ra
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    png_dir = output_dir / "png"
    png_dir.mkdir(exist_ok=True)

    # Bước 1: chuyển PDF sang PNG
    print("=" * 60)
    print("Bước 1: Chuyển PDF thành ảnh PNG")
    print("=" * 60)
    png_names = pdf_to_png(pdf_file,
                           png_dir,
                           dpi=dpi,
                           inpaint=inpaint,
                           inpaint_method=inpaint_method,
                           force_regenerate=True, 
                           make_wide_screen=True)
    # Tái sử dụng danh sách các tệp PNG đã tạo để tạo tệp PDF.
    
    png_files = [png_dir / name for name in png_names]

    # Bước 2: đọc file JSON
    print("\n" + "=" * 60)
    print("Bước 2: Đọc file JSON của PaddleOCR")
    print("=" * 60)
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Bước 2.5: điều chỉnh dữ liệu sang 16:9
    print("\n" + "=" * 60)
    print("Bước 2.5: Điều chỉnh dữ liệu sang tỉ lệ 16:9")
    print("=" * 60)
    data = make_data_wide_screen(data)

    # Bước 3: tạo PPT
    print("\n" + "=" * 60)
    print("Bước 3: Tạo PPT từ JSON của PaddleOCR")
    print("=" * 60)

    # Lấy kích thước PDF
    pdf_size = get_pdf_size_from_data(data)
    print(f"Kích thước PDF theo dữ liệu: {pdf_size[0]} x {pdf_size[1]}")

    # Thiết lập PPT và điều chỉnh toạ độ dữ liệu
    presentation, ppt_width, ppt_height = setup_presentation(pdf_size)
    data = resize_data(data, pdf_size, (ppt_width, ppt_height))
    pdf_size = get_pdf_size_from_data(data)
    scale = ppt_width / pdf_size[0]
    assert abs(scale - 1.0) < 1e-2, "scale sau resize_data nên ≈ 1"
    scale = 1.0
    
    # Cập nhật tham chiếu dữ liệu
    layout_results = data.get('layoutParsingResults', [])
    ocr_results = data.get('ocrResults', [])

    font_name = "Calibri"

    # Xử lý từng trang
    for page_idx in range(len(layout_results)):
        print(f"Đang xử lý trang {page_idx+1}/{len(layout_results)}...")
        slide = presentation.Slides.Append()

        page_layout = layout_results[page_idx]['prunedResult']
        page_ocr = ocr_results[page_idx]['prunedResult']

        parsing_res_list = page_layout.get('parsing_res_list', [])
        ocr_boxes = page_ocr.get('rec_boxes', [])

        # Xử lý khối văn bản
        process_text_blocks(slide, parsing_res_list, ocr_boxes, scale,
                            ppt_width, ppt_height, font_name)

        # Xử lý ảnh nền (bao gồm trích phần tử tiền cảnh và xóa vùng)
        if page_idx < len(png_files):
            process_slide_background(slide, presentation, parsing_res_list,
                                     png_files[page_idx], pdf_size, scale,
                                     png_dir, page_idx)

    # Lưu và chỉnh sửa file PPT
    if out_ppt_name is None:
        out_ppt_name = os.path.basename(pdf_file).replace('.pdf', '.pptx')
    final_ppt_file = output_dir / out_ppt_name
    presentation.SaveToFile(str(final_ppt_file), FileFormat.Pptx2019)
    clean_ppt(str(final_ppt_file), str(final_ppt_file))
    print(f"\nHoàn thành! Tệp đầu ra: {final_ppt_file}")


# ============================================================================
# Nhập dòng lệnh
# ============================================================================


def main():
    """Chức năng nhập lệnh dòng"""
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(
        description="Tạo PPT trực tiếp từ JSON của PaddleOCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
python create_with_paddle_reorg.py result.json input.pdf -o output --dpi 150
        """)
    parser.add_argument("json_file", help="Đường dẫn tới file PaddleOCR JSON (result.json)")
    parser.add_argument("pdf_file", help="Đường dẫn tới file PDF gốc")
    parser.add_argument("--workspace",
                        default="output",
                        type=str,
                        help="Thư mục làm việc (mặc định: output)")
    parser.add_argument('--name', type=str, default=None)
    parser.add_argument("--dpi", type=int, default=150, help="Độ phân giải ảnh (mặc định: 150)")

    args = parser.parse_args()

    workspace = Path(args.workspace)
    out_dir = workspace / os.path.basename(args.pdf_file).replace('.pdf', '')
    out_dir.mkdir(exist_ok=True, parents=True)

    create_ppt_from_paddle_json(args.json_file,
                                args.pdf_file,
                                str(out_dir),
                                out_ppt_name=args.name,
                                dpi=args.dpi)


if __name__ == "__main__":
    main()
