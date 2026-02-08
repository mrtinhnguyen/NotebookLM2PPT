# Kịch bản OCR tổng hợp và phân tích bố cục
import os
import base64
import requests
import json
from typing import Dict, Optional


class PP_OCR:
    """Bộ xử lý OCR và phân tích bố cục PDF"""
    
    # Cấu hình API
    API_CONFIG = {
        "PP-OCRv5": {
            "url": "https://acz08b47m6tcndc6.aistudio-app.com/ocr",
            "params": {
                "useDocOrientationClassify": False,
                "useDocUnwarping": False,
                "useTextlineOrientation": False,
            }
        },
        "PaddleOCR-VL-1.5": {
            "url": "https://f26bq3abj7sal2f8.aistudio-app.com/layout-parsing",
            "params": {
                "useDocOrientationClassify": False,
                "useDocUnwarping": False,
                "useChartRecognition": False,
            }
        },
        "PP-StructureV3": {
            "url": "https://cczfe2v4c2qb0cv9.aistudio-app.com/layout-parsing",
            "params": {
                "useDocOrientationClassify": False,
                "useDocUnwarping": False,
                "useTextlineOrientation": False,
                "useChartRecognition": False,
            }
        }
    }
    
    def __init__(self, token: str):
        """
        Khởi tạo bộ xử lý OCR

        Tham số:
            token: Mã truy cập API
        """
        self.token = token
        self.headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json"
        }
    
    def process_pdf(self, file_path: str, api_type: str, output_path: str) -> Dict:
        """
        Xử lý tệp PDF, gọi API được chỉ định

        Tham số:
            file_path: Đường dẫn tệp PDF
            api_type: Loại API cần gọi, ví dụ "PP-OCRv5", "PaddleOCR-VL-1.5", "PP-StructureV3"
            output_path: Đường dẫn tệp đầu ra

        Trả về:
            Dictionary chứa kết quả gọi API
        """
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Tệp không tồn tại: {file_path}")
        
        if api_type not in self.API_CONFIG:
            print(f"Cảnh báo: Loại API không xác định '{api_type}', bỏ qua")
            return {"status": "failed", "error": f"Loại API không xác định '{api_type}'"}
        
        # Tạo thư mục đầu ra
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Đọc và mã hóa tệp PDF
        with open(file_path, "rb") as file:
            file_bytes = file.read()
            file_data = base64.b64encode(file_bytes).decode("ascii")
        
        config = self.API_CONFIG[api_type]
        
        print(f"Đang gọi {api_type} API...")
        
        try:
            # Xây dựng payload yêu cầu
            payload = {
                "file": file_data,
                "fileType": 0,  # 0: PDF, 1: Hình ảnh
            }
            payload.update(config["params"])
            
            # Gửi yêu cầu
            response = requests.post(config["url"], json=payload, headers=self.headers)
            
            if response.status_code != 200:
                print(f"❌ {api_type} API thất bại: HTTP {response.status_code}")
                return {"status": "failed", "code": response.status_code}
            
            # Lấy kết quả
            result = response.json().get("result")
            
            # Lưu kết quả
            with open(output_path, "w", encoding="utf-8") as json_file:
                json.dump(result, json_file, ensure_ascii=False, indent=4)
            
            print(f"✓ {api_type} API xử lý thành công, kết quả đã lưu vào: {output_path}")
            return {"status": "success", "output_file": output_path}
                
        except Exception as e:
            print(f"❌ {api_type} API gặp lỗi: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    def merge_results(self, vl_path: str, v5_path: str, output_path: str) -> None:
        """
        Hợp nhất kết quả của PaddleOCR-VL và PP-OCRv5

        Tham số:
            vl_path: Đường dẫn tệp kết quả PaddleOCR-VL-1.5
            v5_path: Đường dẫn tệp kết quả PP-OCRv5
            output_path: Đường dẫn tệp đầu ra đã hợp nhất
        """
        print(f"Loading {vl_path}...")
        with open(vl_path, 'r', encoding='utf-8') as f:
            vl_data = json.load(f)
            
        print(f"Loading {v5_path}...")
        with open(v5_path, 'r', encoding='utf-8') as f:
            v5_data = json.load(f)
            
        # Tạo dictionary đã hợp nhất
        merged_result = {}
        
        # 1. Sao chép toàn bộ nội dung vl_data (chủ yếu chứa layoutParsingResults)
        merged_result.update(vl_data)
        
        # 2. Sao chép ocrResults từ v5_data
        if 'ocrResults' in v5_data:
            merged_result['ocrResults'] = v5_data['ocrResults']
            print(f"Added ocrResults from {v5_path}")
        
        # 3. Nếu vl_data không có ocrResults mà v5 có, đảm bảo không bị mất
        # Ngược lại, nếu v5 có layout mà vl không có, cũng có thể xem xét hợp nhất,
        # nhưng lấy layout của vl làm chuẩn.
        
        # 4. Kiểm tra metadata
        if 'dataInfo' not in merged_result and 'dataInfo' in v5_data:
            merged_result['dataInfo'] = v5_data['dataInfo']
            
        # Lưu kết quả
        print(f"Saving merged result to {output_path}...")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_result, f, ensure_ascii=False, indent=4)
        
        print("Done!")
    
    def process_with_vl_and_v5(self, file_path: str, output_dir: str, overwrite: bool = False) -> Optional[str]:
        """
        Sử dụng kết hợp PaddleOCR-VL-1.5 + PP-OCRv5 để xử lý PDF

        Tham số:
            file_path: Đường dẫn tệp PDF
            output_dir: Thư mục đầu ra

        Trả về:
            Đường dẫn tệp kết quả hợp nhất, trả về None nếu thất bại
        """
        vl_output = os.path.join(output_dir, "result_vl.json")
        v5_output = os.path.join(output_dir, "result_v5.json")
        merged_output = os.path.join(output_dir, "result.json")
        if overwrite is False and os.path.exists(merged_output):
            print(f"Kết quả hợp nhất đã tồn tại, bỏ qua xử lý: {merged_output}")
            return merged_output
        
        # Gọi PaddleOCR-VL-1.5
        result = self.process_pdf(file_path, "PaddleOCR-VL-1.5", vl_output)
        if result.get("status") != "success":
            print("PaddleOCR-VL-1.5 xử lý thất bại, bỏ qua bước hợp nhất")
            return None
        
        # Gọi PP-OCRv5
        result = self.process_pdf(file_path, "PP-OCRv5", v5_output)
        if result.get("status") != "success":
            print("PP-OCRv5 xử lý thất bại, bỏ qua bước hợp nhất")
            return None
        
        # Hợp nhất kết quả
        self.merge_results(vl_output, v5_output, merged_output)
        return merged_output
    
    def process_with_structure(self, file_path: str, output_dir: str, overwrite: bool = False) -> Optional[str]:
        """
        Sử dụng PP-StructureV3 để xử lý PDF

        Tham số:
            file_path: Đường dẫn tệp PDF
            output_dir: Thư mục đầu ra

        Trả về:
            Đường dẫn tệp kết quả, trả về None nếu thất bại
        """
        structure_output = os.path.join(output_dir, "result_structure.json")
        if overwrite is False and os.path.exists(structure_output):
            print(f"Kết quả cấu trúc đã tồn tại, bỏ qua xử lý: {structure_output}")
            return structure_output
        result = self.process_pdf(file_path, "PP-StructureV3", structure_output)
        
        if result.get("status") != "success":
            print("PP-StructureV3 xử lý thất bại")
            return None
        
        return structure_output


def main():
    """Hàm chính"""
    # Tải biến môi trường
    from dotenv import load_dotenv
    load_dotenv()
    TOKEN = os.getenv("TOKEN")
    
    if not TOKEN:
        raise ValueError("Không tìm thấy biến môi trường TOKEN, vui lòng kiểm tra tệp .env")

    # Đường dẫn tệp cấu hình
    file_path = r"examples/Floyd_thuat_toan_quy_hoach_dong.pdf"
    output_dir = "output/Floyd_thuat_toan_quy_hoach_dong"
    
    # Khởi tạo bộ xử lý
    processor = PP_OCR(TOKEN)
    
    # Chọn phương pháp xử lý
    methods = ['PaddleOCR-VL-1.5+PP-OCRv5', 'PP-StructureV3']
    method = methods[1]  # Phương pháp lựa chọn
    
    if method == 'PaddleOCR-VL-1.5+PP-OCRv5':
        processor.process_with_vl_and_v5(file_path, output_dir)
    elif method == 'PP-StructureV3':
        processor.process_with_structure(file_path, output_dir)
    else:
        raise ValueError(f"Phương pháp không xác định: {method}")
    


if __name__ == "__main__":
    main()
