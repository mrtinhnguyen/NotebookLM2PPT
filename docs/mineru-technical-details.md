# MinerU 深度优化 - 技术实现细节

本文档详细说明了 NotebookLM2PPT 中 MinerU 深度优化功能的技术实现细节。

## 目录

- [核心模块](#核心模块)
- [智能文本框筛选](#智能文本框筛选)
- [字体统一处理](#字体统一处理)
- [高质量图片替换](#高质量图片替换)
- [智能背景处理](#智能背景处理)
- [完整工作流程](#完整工作流程)

---

## 核心模块

MinerU 优化功能的核心实现在 `notebooklm2ppt/utils/ppt_refiner.py` 文件中。

主要函数：

```python
def refine_ppt(tmp_image_dir, json_file, ppt_file, png_dir, png_files, final_out_ppt_file)
```

该函数接收以下参数：
- `tmp_image_dir`: 临时图片目录，用于存储下载的 MinerU 图片
- `json_file`: MinerU 生成的 JSON 文件路径
- `ppt_file`: 基础转换生成的 PPT 文件路径
- `png_dir`: PDF 转换生成的 PNG 图片目录
- `png_files`: PNG 文件列表
- `final_out_ppt_file`: 最终输出的优化后 PPT 文件路径

---

## 智能文本框筛选

### 问题背景

在基础转换过程中，微软电脑管家的智能圈选功能可能会识别出一些无关的文本框，这些文本框与 PDF 的实际内容不匹配，需要被过滤掉。

### 解决方案：IOU 算法

程序使用 IOU（Intersection over Union，交并比）算法来评估文本框与 PDF 内容块的重叠程度。

#### IOU 计算实现

```python
def compute_iou(boxA, boxB):
    # box = [left, top, right, bottom]
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interWidth = max(0, xB - xA)
    interHeight = max(0, yB - yA)
    interArea = interWidth * interHeight

    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    iou = interArea / float(boxAArea + boxBArea - interArea)

    return iou
```

#### 文本框筛选逻辑

```python
def compute_ious(left, top, height, width, scaled_para_blocks):
    bbox = [left, top, left + width, top + height]
    ious = []
    for block in scaled_para_blocks:
        block_bbox = block['bbox']
        iou = compute_iou(bbox, block_bbox)
        ious.append(iou)
    return ious
```

#### 筛选决策

```python
ious = compute_ious(left, top, height, width, scaled_para_blocks)

if np.max(ious) > 0.01:
    # IOU > 0.01，认为该文本框有效，予以保留
    nearest_block = scaled_para_blocks[np.argmax(ious)]
    if nearest_block['type'] in ['title', 'text']:
        # 保留文本框
        pass
else:
    # IOU <= 0.01，认为该文本框无效，删除
    slide.Shapes.RemoveAt(i)
```

### 阈值选择说明

- **阈值 0.01**：经过实验验证，0.01 是一个合理的阈值
  - 过高（如 0.1）：可能误删一些有效的文本框
  - 过低（如 0.001）：可能保留过多无关文本框
- 该阈值可以根据实际使用情况进行调整

---

## 字体统一处理

### 问题背景

基础转换生成的 PPT 中，文本框的字体可能各不相同，影响演示文稿的专业性和可读性。

### 解决方案：统一字体为"微软雅黑"

```python
from spire.presentation import *

# 创建微软雅黑字体对象
newFont = TextFont("微软雅黑")

# 遍历文本框中的所有文本范围
for textRange in paragraph.TextRanges:
    textRange.LatinFont = newFont
```

### 实现细节

1. **遍历所有形状**：从后向前遍历幻灯片中的所有形状
2. **识别文本框**：检查形状类型是否为 `IAutoShape`
3. **统一字体**：将所有文本范围的拉丁字体设置为"微软雅黑"

```python
for i in range(slide.Shapes.Count - 1, -1, -1):
    shape = slide.Shapes[i]
    
    # 只处理文本框
    if "IAutoShape" not in str(type(shape)):
        continue
    
    # 获取第一个段落
    paragraph = shape.TextFrame.Paragraphs[0]
    
    # 统一字体
    for textRange in paragraph.TextRanges:
        textRange.LatinFont = newFont
```

---

## 高质量图片替换

### 问题背景

基础转换过程中，图片可能被压缩或质量降低，无法满足高质量演示的需求。

### 解决方案：从 MinerU JSON 提取原始高清图片

#### 图片下载实现

```python
import requests
import os

def download_image(image_url, tmp_image_path):
    if os.path.exists(tmp_image_path):
        return  # 避免重复下载
    
    response = requests.get(image_url)
    with open(tmp_image_path, 'wb') as f:
        f.write(response.content)
```

#### 图片替换逻辑

```python
from spire.presentation import *

# 获取所有图片块
image_blocks = get_scaled_para_blocks(ppt_scale, pdf_info, page_index, 'only_image')

for image_block in image_blocks:
    for line in image_block['lines']:
        for span in line['spans']:
            # 从 MinerU JSON 获取图片路径
            image_path = span['image_path']
            tmp_image_path = os.path.join(tmp_image_dir, os.path.basename(image_path))
            
            # 下载高清图片
            download_image(image_path, tmp_image_path)
            
            # 获取图片位置
            left, top, right, bottom = image_block['bbox']
            rect1 = RectangleF.FromLTRB(left, top, right, bottom)
            
            # 替换 PPT 中的图片
            image = slide.Shapes.AppendEmbedImageByPath(ShapeType.Rectangle, tmp_image_path, rect1)
            image.Line.FillType = FillFormatType.none
            image.ZOrderPosition = 0  # 设置图片在最底层
```

### 优势

- **保留原始质量**：直接使用 MinerU 解析的原始图片，避免二次压缩
- **准确位置**：基于 MinerU 的 bbox 信息精确定位图片位置
- **自动下载**：程序自动处理图片下载，无需手动操作

---

## 智能背景处理

### 问题背景

PPT 的背景处理需要平衡两个目标：
1. 纯色区域应该填充为纯色，避免不必要的纹理
2. 复杂背景区域应该保留原背景，避免丢失设计元素

### 解决方案：基于边缘多样性和颜色差异的智能判断

#### 边缘多样性检测

```python
import numpy as np
import cv2

def compute_edge_diversity(image_cv, left, top, right, bottom):
    left, top, right, bottom = int(left), int(top), int(right), int(bottom)
    
    # 提取四条边缘
    top_edge = image_cv[top:top+1, left:right]
    bottom_edge = image_cv[bottom-1:bottom, left:right]
    left_edge = image_cv[top:bottom, left:left+1]
    right_edge = image_cv[top:bottom, right-1:right]
    
    edges = [top_edge, bottom_edge, left_edge, right_edge]
    
    # 计算每条边缘的颜色标准差
    diversity = np.max([edge.astype(np.float32).reshape(-1, 3).std(axis=0).mean() for edge in edges])
    
    return diversity
```

#### 四点颜色差异计算

```python
def compute_color_diff(color1, color2):
    # 转换到 CIELAB 颜色空间，避免 uint8 相减时的环绕问题
    color1_lab = cv2.cvtColor(np.uint8([[color1]]), cv2.COLOR_RGB2Lab)[0][0].astype(np.float32)
    color2_lab = cv2.cvtColor(np.uint8([[color2]]), cv2.COLOR_RGB2Lab)[0][0].astype(np.float32)
    diff = np.linalg.norm(color1_lab - color2_lab)
    return float(diff)

def compute_four_point_diff(image_cv, left, top, right, bottom):
    left, top, right, bottom = int(left), int(top), int(right), int(bottom)
    
    # 获取四个角的颜色
    top_left = image_cv[top, left]
    top_right = image_cv[top, right-1]
    bottom_left = image_cv[bottom-1, left]
    bottom_right = image_cv[bottom-1, right-1]
    
    # 计算四个角之间的颜色差异
    diffs = [
        compute_color_diff(top_left, top_right),
        compute_color_diff(top_left, bottom_left),
        compute_color_diff(bottom_right, top_right),
        compute_color_diff(bottom_right, bottom_left),
    ]
    
    return np.mean(diffs)
```

#### 智能处理决策

```python
for text_block in text_blocks:
    bbox = text_block['bbox']
    l, t, r, b = map(int, bbox)
    
    # 计算填充颜色（左上角和右下角的平均值）
    fill_color = image_cv[t, l] * 0.5 + image_cv[b, r] * 0.5
    fill_color = fill_color.astype(np.uint8).tolist()
    
    # 计算边缘多样性和四点差异
    diversity = compute_edge_diversity(image_cv, l, t, r, b)
    diff = compute_four_point_diff(image_cv, l, t, r, b)
    
    # 智能决策
    if diversity < 10 and diff < 9:
        # 纯色区域，填充平均颜色
        cv2.rectangle(image_cv, (l, t), (r, b), fill_color, thickness=-1)
    else:
        # 复杂背景，保留原背景
        image_cv[t:b, l:r] = old_bg_cv[t:b, l:r]
```

### 阈值说明

- **边缘多样性阈值 10**：
  - < 10：边缘颜色变化小，认为是纯色区域
  - ≥ 10：边缘颜色变化大，认为是复杂区域

- **四点差异阈值 9**：
  - < 9：四个角颜色差异小，认为是纯色区域
  - ≥ 9：四个角颜色差异大，认为是复杂区域

这两个阈值经过实验验证，能够较好地区分纯色和复杂背景。

---

## 完整工作流程

### 数据准备

```python
# 1. 加载 MinerU JSON
data = load_json(json_file)
pdf_info = data['pdf_info']

# 2. 根据页码筛选信息
indices = get_indices_from_png_names(png_files)
pdf_info = [pdf_info[i] for i in indices]

# 3. 计算缩放比例
pdf_w, _ = pdf_info[0]['page_size']
presentation = Presentation()
presentation.LoadFromFile(ppt_file)
ppt_H, ppt_W = presentation.SlideSize.Size.Height, presentation.SlideSize.Size.Width
ppt_scale = ppt_W / pdf_w
```

### 逐页处理

```python
for page_index, slide in enumerate(presentation.Slides):
    print(f"优化 第 {page_index+1}/{len(png_files)} 页...")
    
    # 1. 获取缩放后的文本块
    scaled_para_blocks = get_scaled_para_blocks(ppt_scale, pdf_info, page_index)
    
    # 2. 智能文本框筛选和字体统一
    for i in range(slide.Shapes.Count - 1, -1, -1):
        shape = slide.Shapes[i]
        
        if "IAutoShape" not in str(type(shape)):
            slide.Shapes.RemoveAt(i)
            continue
        
        paragraph = shape.TextFrame.Paragraphs[0]
        left, top, text, width, height = shape.Left, shape.Top, shape.TextFrame.Text, shape.Width, shape.Height
        
        # 计算 IOU
        ious = compute_ious(left, top, height, width, scaled_para_blocks)
        
        if np.max(ious) > 0.01:
            # 保留文本框并统一字体
            nearest_block = scaled_para_blocks[np.argmax(ious)]
            if nearest_block['type'] in ['title', 'text']:
                newFont = TextFont("微软雅黑")
                for textRange in paragraph.TextRanges:
                    textRange.LatinFont = newFont
        else:
            # 删除无效文本框
            slide.Shapes.RemoveAt(i)
    
    # 3. 高质量图片替换
    image_blocks = get_scaled_para_blocks(ppt_scale, pdf_info, page_index, 'only_image')
    for image_block in image_blocks:
        for line in image_block['lines']:
            for span in line['spans']:
                tmp_image_path = os.path.join(tmp_image_dir, os.path.basename(span['image_path']))
                download_image(span['image_path'], tmp_image_path)
                
                left, top, right, bottom = image_block['bbox']
                rect1 = RectangleF.FromLTRB(left, top, right, bottom)
                image = slide.Shapes.AppendEmbedImageByPath(ShapeType.Rectangle, tmp_image_path, rect1)
                image.Line.FillType = FillFormatType.none
                image.ZOrderPosition = 0
    
    # 4. 智能背景处理
    background = slide.SlideBackground
    old_bg_file = "old_bg.png"
    background.Fill.PictureFill.Picture.EmbedImage.Image.Save(old_bg_file)
    old_bg_cv = np.array(Image.open(old_bg_file))
    os.remove(old_bg_file)
    
    background.Type = BackgroundType.Custom
    background.Fill.FillType = FillFormatType.Picture
    
    png_file = png_files[page_index]
    image_cv = Image.open(png_file)
    image_cv = np.array(image_cv)
    
    image_h, image_w, _ = image_cv.shape
    old_bg_cv = cv2.resize(old_bg_cv, (image_w, image_h), interpolation=cv2.INTER_CUBIC)
    
    image_scale = image_w / pdf_w
    text_blocks = get_scaled_para_blocks(image_scale, pdf_info, page_index, cond='no_image')
    
    for text_block in text_blocks:
        bbox = text_block['bbox']
        l, t, r, b = map(int, bbox)
        
        fill_color = image_cv[t, l] * 0.5 + image_cv[b, r] * 0.5
        fill_color = fill_color.astype(np.uint8).tolist()
        
        diversity = compute_edge_diversity(image_cv, l, t, r, b)
        diff = compute_four_point_diff(image_cv, l, t, r, b)
        
        if diversity < 10 and diff < 9:
            cv2.rectangle(image_cv, (l, t), (r, b), fill_color, thickness=-1)
        else:
            image_cv[t:b, l:r] = old_bg_cv[t:b, l:r]
    
    tmp_bg_file = png_file.replace('.png', '_bg.png')
    Image.fromarray(image_cv).save(tmp_bg_file)
    stream = Stream(tmp_bg_file)
    
    imageData = presentation.Images.AppendStream(stream)
    background.Fill.PictureFill.FillType = PictureFillType.Stretch
    background.Fill.PictureFill.Picture.EmbedImage = imageData
```

### 保存结果

```python
presentation.SaveToFile(final_out_ppt_file, FileFormat.Pptx2019)
print(f"优化完成! 输出文件: {final_out_ppt_file}")

# 清理 PPT
clean_ppt(final_out_ppt_file, final_out_ppt_file)
```

---

## 性能优化建议

1. **图片缓存**：已下载的图片会缓存到 `tmp_image_dir`，避免重复下载
2. **并行处理**：对于大型文档，可以考虑并行处理多个页面
3. **内存管理**：处理完每页后及时释放临时变量，避免内存占用过高

---

## 故障排查

### 常见问题

1. **图片下载失败**
   - 检查网络连接
   - 确认 MinerU JSON 中的图片 URL 是否有效

2. **文本框筛选不准确**
   - 调整 IOU 阈值（当前为 0.01）
   - 检查 MinerU JSON 的解析质量

3. **背景处理效果不理想**
   - 调整边缘多样性阈值（当前为 10）
   - 调整四点差异阈值（当前为 9）

---

## 参考资料

- [MinerU 官方文档](https://mineru.net/)
- [Spire.Presentation 文档](https://www.e-iceblue.com/Introduce/presentation-for-net.html)
- [OpenCV 文档](https://docs.opencv.org/)
- [NumPy 文档](https://numpy.org/doc/)
