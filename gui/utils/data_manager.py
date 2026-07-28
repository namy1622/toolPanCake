"""
data_manager.py - Module quản lý đọc/ghi dữ liệu cho Pancake Control GUI.
Đọc appsettings.json, quét file JSON trong thư mục data/, đọc CSV output.
"""

import csv
import json
import os
import re
from typing import Dict, List, Optional


# Cấu hình các trang Pancake (đồng bộ với scripts)
PAGES = {
    "1": {"name": "Dây Thìa Canh", "folder": "DayThiaCanh", "url": "https://pancake.vn/571938736002434"},
    "2": {"name": "Trà Đông Trùng", "folder": "TraDongTrung", "url": "https://pancake.vn/941461145712453"},
}


def get_workspace_dir() -> str:
    """Xác định thư mục gốc dự án (WORKSPACE_DIR) từ vị trí file hiện tại."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # gui/utils/ -> gui/ -> workspace root
    return os.path.dirname(os.path.dirname(current_dir))


def load_appsettings() -> Dict:
    """Đọc file appsettings.json và trả về dict cấu hình."""
    workspace = get_workspace_dir()
    settings_path = os.path.join(workspace, "appsettings.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Lỗi đọc appsettings.json: {e}")
    return {}


def get_model_names() -> List[str]:
    """Lấy danh sách tên model AI từ appsettings.json."""
    settings = load_appsettings()
    return list(settings.keys())


def get_json_files(page: str, date: str) -> List[Dict]:
    """
    Quét thư mục data/{folder}/{date}/ và trả về danh sách file JSON.
    Mỗi file trả về: {"name": ..., "size": ..., "is_processed": True/False}
    """
    if page not in PAGES:
        return []

    workspace = get_workspace_dir()
    folder_name = PAGES[page]["folder"]
    dir_path = os.path.join(workspace, "data", folder_name, date)

    if not os.path.exists(dir_path):
        return []

    files = []
    try:
        for fname in os.listdir(dir_path):
            if fname.endswith(".json"):
                file_path = os.path.join(dir_path, fname)
                size = os.path.getsize(file_path)
                files.append({
                    "name": fname,
                    "size": size,
                    "is_processed": fname.startswith("done_")
                })

        # Sắp xếp theo index ở đầu tên file
        def get_file_index(filename):
            match = re.match(r'^(?:done_)?(\d+)_', filename)
            return int(match.group(1)) if match else 999999

        files.sort(key=lambda x: get_file_index(x["name"]))
    except Exception as e:
        print(f"Lỗi quét thư mục data: {e}")

    return files


def read_json_file(page: str, date: str, filename: str) -> Optional[Dict]:
    """Đọc nội dung 1 file JSON chat."""
    if page not in PAGES:
        return None

    workspace = get_workspace_dir()
    folder_name = PAGES[page]["folder"]
    file_path = os.path.join(workspace, "data", folder_name, date, filename)

    if not os.path.exists(file_path):
        # Thử tìm với/không prefix done_
        if filename.startswith("done_"):
            alt = filename[5:]
        else:
            alt = f"done_{filename}"
        file_path = os.path.join(workspace, "data", folder_name, date, alt)

    if not os.path.exists(file_path):
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Lỗi đọc file JSON {filename}: {e}")
        return None


def read_csv_data(page: str, date: str) -> List[Dict]:
    """Đọc file CSV output và trả về danh sách dict."""
    if page not in PAGES:
        return []

    workspace = get_workspace_dir()
    folder_name = PAGES[page]["folder"]
    csv_path = os.path.join(workspace, "output", folder_name, f"{date}.csv")

    if not os.path.exists(csv_path):
        return []

    results = []
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(line for line in f if not line.startswith('#'))
            for row in reader:
                results.append({
                    "source_file": row.get("File Nguồn", ""),
                    "name": row.get("Tên Khách Hàng", ""),
                    "phone": row.get("Số Điện Thoại", ""),
                    "address": row.get("Địa Chỉ", ""),
                    "price": row.get("Giá Chốt", ""),
                    "quantity": row.get("Số Lượng Hộp/KG", ""),
                    "product_name": row.get("Tên Sản Phẩm", ""),
                })
    except Exception as e:
        print(f"Lỗi đọc CSV: {e}")

    return results


def get_output_folder_path(page: str) -> str:
    """Trả về đường dẫn thư mục output của page đã chọn."""
    if page not in PAGES:
        return ""
    workspace = get_workspace_dir()
    folder_name = PAGES[page]["folder"]
    path = os.path.join(workspace, "output", folder_name)
    os.makedirs(path, exist_ok=True)
    return path
