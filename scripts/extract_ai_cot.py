import os
import json
import requests
import csv
import glob
import sys
import re
import time
import datetime

# Đảm bảo luồng xuất dữ liệu luôn dùng UTF-8 trên Windows để không bị lỗi CP1252
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Tự động xác định thư mục gốc của dự án
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(SCRIPT_DIR) == 'scripts':
    WORKSPACE_DIR = os.path.dirname(SCRIPT_DIR)
else:
    WORKSPACE_DIR = SCRIPT_DIR

# Danh sách page
PAGES = {
    "1": {"name": "Dây Thìa Canh", "folder": "DayThiaCanh"},
    "2": {"name": "Trà Đông Trùng", "folder": "TraDongTrung"},
}

# Đọc arguments từ Server
arg_page = None
arg_model = None
arg_date = None

if len(sys.argv) > 1:
    arg_page = sys.argv[1].strip()
if len(sys.argv) > 2:
    arg_model = sys.argv[2].strip()
if len(sys.argv) > 3:
    arg_date = sys.argv[3].strip()

# Chọn page
if arg_page:
    page_choice = arg_page
    print(f"Nhận tham số dòng lệnh page: {page_choice}")
else:
    print("=" * 50)
    print(" CHỌN PAGE CẦN PHÂN TÍCH")
    print("=" * 50)
    for key, val in PAGES.items():
        print(f" {key}. {val['name']}")
    page_choice = input("\nNhập số thứ tự để chọn (Mặc định 1): ").strip() or "1"

if page_choice not in PAGES:
    page_choice = "1"
selected_page = PAGES[page_choice]
PAGE_FOLDER = selected_page["folder"]
print(f"\n-> Đã chọn page: {selected_page['name']}")
print("-" * 50)

# Đọc cấu hình AI từ appsettings.json
SETTINGS_FILE = os.path.join(WORKSPACE_DIR, "appsettings.json")
try:
    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
        settings = json.load(f)
        keys = list(settings.keys())
        
        if arg_model:
            # Check if arg_model is an index or key
            if arg_model in keys:
                selected_key = arg_model
            else:
                try:
                    idx = int(arg_model) - 1
                    if 0 <= idx < len(keys):
                        selected_key = keys[idx]
                    else:
                        selected_key = keys[0]
                except:
                    matched_key = None
                    for key in keys:
                        if arg_model.lower() in key.lower():
                            matched_key = key
                            break
                    selected_key = matched_key if matched_key else keys[0]
            print(f"Nhận tham số dòng lệnh AI model: {selected_key}")
        else:
            print("\n" + "=" * 50)
            print(" CHỌN MÔ HÌNH AI ĐỂ XỬ LÝ DỮ LIỆU")
            print("=" * 50)
            for i, key in enumerate(keys, 1):
                model_name = settings[key].get("Model", "Unknown")
                print(f" {i}. {key} (Model: {model_name})")
                
            choice = input("\nNhập số thứ tự để chọn (Mặc định 1): ")
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(keys):
                    idx = 0
            except:
                idx = 0
                
            selected_key = keys[idx]
            
        print(f"\n-> Đang khởi động AI với cấu hình: {selected_key}")
        print("-" * 50)
        
        ai_settings = settings[selected_key]
        API_KEY = ai_settings.get("ApiKey", "")
        API_URL = ai_settings.get("ApiUrl", "")
        MODEL = ai_settings.get("Model", "")
except Exception as e:
    print(f"Lỗi khi đọc file cấu hình appsettings.json: {e}")
    sys.exit(1)

# Đường dẫn data và output theo page + ngày
if arg_date:
    print(f"Nhận tham số dòng lệnh ngày (date): {arg_date}")
    today_str = arg_date
else:
    today_str = datetime.datetime.now().strftime("%d.%m.%y")
    print(f"Không có tham số ngày dòng lệnh. Mặc định ngày hiện tại: {today_str}")

DATA_DIR = os.path.join(WORKSPACE_DIR, "data", PAGE_FOLDER, today_str)
print(f"Thư mục dữ liệu nguồn quét: {DATA_DIR}")
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "output", PAGE_FOLDER)
OUTPUT_CSV = os.path.join(OUTPUT_DIR, f"{today_str}.csv")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_info_with_ai(chat_text):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = """Bạn là trợ lý trích xuất thông tin khách hàng từ đoạn chat mua hàng. Nhiệm vụ: Tìm và trích xuất Tên khách hàng, Số điện thoại, Địa chỉ, Giá chốt cuối cùng, và Số hộp.
QUY TẮC TỐI THƯỢNG:
1. Bạn phải COPY Y HỆT từng chữ cái từ tin nhắn của khách cho phần Tên và Địa chỉ.
2. TUYỆT ĐỐI KHÔNG viết hoa chữ cái đầu nếu khách không viết.
3. TUYỆT ĐỐI KHÔNG sửa lỗi chính tả, không tự thêm/bớt từ.
4. KHÔNG tự suy luận địa danh.
5. ĐỊNH DẠNG SỐ HỘP: Bạn bắt buộc phải phân tích kỹ tin nhắn chốt đơn cuối cùng của "Tôi" (Người bán) và ghi ra trường "ly_do_tinh_so_hop" thật ngắn gọn, đủ ý nghĩa trước.
- RẤT QUAN TRỌNG: Nếu có khuyến mãi, phải cộng dồn vào! (Ví dụ: Mua 3 tặng 1 -> 4 hộp; Mua 5 tặng 2 -> 7 hộp; Mua 4 tặng 1 -> 5 hộp; Mua 2 tặng 1 -> 3 hộp).
- Sau khi phân tích xong, mới ghi tổng số hộp thực tế khách nhận vào trường "so_hop" theo định dạng "1h", "2h", "4h", "7h"...

--- VÍ DỤ 1 ---
Khách: gui ve dia chi 123 le loi q1 nhe e 0901234567. minh lay 2 hop nhe, 
Tôi: 3 hộp là 240k miễn ship. Mua 3 tặng 1 (tổng nhận 4 hộp).
Assistant:
{
  "ten": "",
  "sdt": "0901234567",
  "dia_chi": "123 le loi q1",
  "gia_chot": "240000",
  "ly_do_tinh_so_hop": "Người bán (Tôi) chốt cuối cùng là 3 hộp 240k, áp dụng mua 3 tặng 1. Tổng cộng khách nhận 4 hộp.",
  "so_hop": "4h"
}
--- KẾT QUẢ TRẢ VỀ ---
Chỉ trả về 1 khối JSON duy nhất, không có giải thích nào khác:
{
  "ten": "",
  "sdt": "",
  "dia_chi": "",
  "gia_chot": "",
  "ly_do_tinh_so_hop": "",
  "so_hop": ""
}
"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Đoạn chat:\n{chat_text}\n\nLưu ý: Bạn BẮT BUỘC phải xuất kết quả ở dạng JSON thuần túy (không giải thích, không tóm tắt, không phân tích, không thêm bất kỳ chữ nào ngoài JSON). Mẫu:\n{{\n  \"ten\": \"\",\n  \"sdt\": \"\",\n  \"dia_chi\": \"\",\n  \"gia_chot\": \"\",\n  \"ly_do_tinh_so_hop\": \"\",\n  \"so_hop\": \"\"\n}}"}
        ],
        "temperature": 0.1,
    }

    fallback_delays = [5, 3, 6, 10]
    max_retries = len(fallback_delays)
    
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            result = response.json()
            
            content = result['choices'][0]['message']['content']
            
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                json_str = match.group(0)
                return json.loads(json_str)
            else:
                return {"ten": "", "sdt": "", "dia_chi": "", "gia_chot": "", "ly_do_tinh_so_hop": "", "so_hop": ""}
                
        except requests.exceptions.HTTPError as e:
            if 'response' in locals() and response.status_code == 429:
                if attempt >= max_retries:
                    break
                    
                wait_time = fallback_delays[attempt]
                
                try:
                    error_msg = response.json().get('error', {}).get('message', '')
                    time_match = re.search(r'try again in (\d+\.?\d*)s', error_msg)
                    if time_match:
                        groq_wait = float(time_match.group(1)) + 1.0
                        if groq_wait > wait_time:
                            wait_time = groq_wait
                except:
                    pass
                
                print(f"\n [!] Quá tải API. Đang chờ {wait_time:.1f}s để thử lại (Lần {attempt+1}/{max_retries})...", end=" ", flush=True)
                time.sleep(wait_time)
                continue
            else:
                print(f"\nLỗi khi gọi API: {e}")
                if 'response' in locals() and hasattr(response, 'text'):
                    print(f"Chi tiết response: {response.text}")
                return {"ten": "", "sdt": "", "dia_chi": "", "gia_chot": "", "ly_do_tinh_so_hop": "", "so_hop": ""}
        except Exception as e:
            print(f"\nLỗi khi gọi API: {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                print(f"Chi tiết response: {response.text}")
            return {"ten": "", "sdt": "", "dia_chi": "", "gia_chot": "", "ly_do_tinh_so_hop": "", "so_hop": ""}
            
    print(f"\n [!] Bỏ cuộc sau {max_retries} lần thử nghiệm. Bỏ qua file này.")
    return {"ten": "", "sdt": "", "dia_chi": "", "gia_chot": "", "ly_do_tinh_so_hop": "", "so_hop": ""}

def main():
    all_json = glob.glob(os.path.join(DATA_DIR, "*.json"))
    json_files = [f for f in all_json if not os.path.basename(f).startswith("done_")]
    
    if not json_files:
        print(f"Không tìm thấy file JSON nào mới trong: {DATA_DIR}")
        return

    print(f"Tìm thấy {len(json_files)} file lịch sử chat. Bắt đầu dùng AI để phân tích...\n")

    if os.path.exists(OUTPUT_CSV):
        csv_mode = 'a'
        print(f"File '{os.path.basename(OUTPUT_CSV)}' đã tồn tại → Ghi nối thêm.\n")
    else:
        csv_mode = 'w'
        print(f"Tạo file kết quả mới: {os.path.basename(OUTPUT_CSV)}\n")
    
    # Mở file CSV để ghi kết quả
    fieldnames = ['File Nguồn', 'Tên Khách Hàng', 'Số Điện Thoại', 'Địa Chỉ', 'Giá Chốt', 'Số Hộp', 'Lý Do Tính Số Hộp']
    
    # Check if we need to write header (csv_mode == 'w' or file is empty)
    write_header = csv_mode == 'w' or os.path.getsize(OUTPUT_CSV) == 0
    
    with open(OUTPUT_CSV, mode=csv_mode, encoding='utf-8-sig', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        
        if write_header:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            csv_file.write(f"# Thời gian chạy tool: {timestamp}\n")
            writer.writeheader()

        for file_path in json_files:
            file_name = os.path.basename(file_path)
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            messages = data.get('messages', [])
            if not messages:
                continue

            chat_text = ""
            for msg in messages:
                chat_text += f"{msg['sender']}: {msg['content']}\n"
            
            print(f"Đang phân tích file: {file_name}...", end=" ", flush=True)
            start_time = time.time()
            ai_result = extract_info_with_ai(chat_text)
            elapsed_time = round(time.time() - start_time, 2)
            print(f"({elapsed_time}s)")
            
            ten_khach = ai_result.get('ten', '').strip()
            if not ten_khach:
                ten_khach = data.get('customerName', '')

            # Ghi thông tin chi tiết vào CSV
            writer.writerow({
                'File Nguồn': file_name,
                'Tên Khách Hàng': ten_khach,
                'Số Điện Thoại': ai_result.get('sdt', ''),
                'Địa Chỉ': ai_result.get('dia_chi', ''),
                'Giá Chốt': ai_result.get('gia_chot', ''),
                'Số Hộp': ai_result.get('so_hop', ''),
                # 'Lý Do Tính Số Hộp': ai_result.get('ly_do_tinh_so_hop', '')
            })
            
            print(f" -> Tên: {ten_khach} | SĐT: {ai_result.get('sdt', '')} | Địa chỉ: {ai_result.get('dia_chi', '')} | Giá: {ai_result.get('gia_chot', '')} | Số hộp: {ai_result.get('so_hop', '')}")
            
            # Đổi tên file sang "done_" để đánh dấu đã xử lý
            new_file_name = f"done_{file_name}"
            new_file_path = os.path.join(DATA_DIR, new_file_name)
            try:
                os.rename(file_path, new_file_path)
                print(f" -> Đã đổi tên thành: {new_file_name}")
            except Exception as e:
                print(f" -> Lỗi khi đổi tên file: {e}")
            
            # Nghỉ 5s để tránh Rate Limit
            time.sleep(5)

    print(f"\n HOÀN TẤT! Toàn bộ thông tin đã được lưu ra file Excel: {OUTPUT_CSV}")

if __name__ == '__main__':
    main()
