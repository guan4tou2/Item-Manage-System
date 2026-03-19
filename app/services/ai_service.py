"""AI 輔助服務模組：圖片辨識與 OCR 收據掃描"""
import os


# M12: AI Image Recognition
def analyze_image(image_path: str) -> dict:
    """分析圖片並建議物品屬性。
    目前使用檔名關鍵字啟發式方法；可擴充為 OpenAI Vision API 或其他視覺 API。
    """
    filename = os.path.basename(image_path).lower()
    suggestions: dict = {}

    keyword_map = {
        "phone": {"ItemType": "3C產品", "category": "electronics"},
        "mobile": {"ItemType": "3C產品", "category": "electronics"},
        "laptop": {"ItemType": "3C產品", "category": "electronics"},
        "computer": {"ItemType": "3C產品", "category": "electronics"},
        "tablet": {"ItemType": "3C產品", "category": "electronics"},
        "camera": {"ItemType": "3C產品", "category": "electronics"},
        "headphone": {"ItemType": "3C產品", "category": "electronics"},
        "earphone": {"ItemType": "3C產品", "category": "electronics"},
        "book": {"ItemType": "文具", "category": "stationery"},
        "pen": {"ItemType": "文具", "category": "stationery"},
        "notebook": {"ItemType": "文具", "category": "stationery"},
        "chair": {"ItemType": "家具", "category": "furniture"},
        "desk": {"ItemType": "家具", "category": "furniture"},
        "table": {"ItemType": "家具", "category": "furniture"},
        "sofa": {"ItemType": "家具", "category": "furniture"},
        "tool": {"ItemType": "工具", "category": "tools"},
        "drill": {"ItemType": "工具", "category": "tools"},
        "hammer": {"ItemType": "工具", "category": "tools"},
        "wrench": {"ItemType": "工具", "category": "tools"},
        "cloth": {"ItemType": "衣物", "category": "clothing"},
        "shirt": {"ItemType": "衣物", "category": "clothing"},
        "shoe": {"ItemType": "衣物", "category": "clothing"},
        "bag": {"ItemType": "配件", "category": "accessories"},
    }

    for keyword, props in keyword_map.items():
        if keyword in filename:
            suggestions.update(props)
            break

    return {
        "suggestions": suggestions,
        "confidence": "low",
        "method": "filename_heuristic",
    }


# M13: OCR Receipt Scanning
def scan_receipt(image_path: str) -> dict:
    """從收據圖片中提取採購資訊。
    目前回傳佔位符；可擴充為 Tesseract OCR 或雲端 OCR API。
    """
    return {
        "detected": False,
        "message": "OCR 功能需要安裝 Tesseract 或設定雲端 OCR API",
        "data": {},
    }
