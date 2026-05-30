import os
import json
import requests
import csv
import glob
import sys
import re
import time
# Cấu hình đường dẫn
WORKSPACE_DIR = r"F:\tool_cao_data"

# Đọc cấu hình từ appsettings.json
SETTINGS_FILE = os.path.join(WORKSPACE_DIR, "appsettings.json")
try:
    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
        settings = json.load(f)
        
        print("=" * 50)
        print(" CHỌN MÔ HÌNH AI ĐỂ XỬ LÝ DỮ LIỆU")
        print("=" * 50)
        keys = list(settings.keys())
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


DATA_DIR = os.path.join(WORKSPACE_DIR, "data")
OUTPUT_CSV = os.path.join(WORKSPACE_DIR, "danh_sach_khach_hang.csv")

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

# 5. Với số điện thoại thì thêm ký tự ' ở đầu bởi sẽ bị mất số 0 ở đầu trong Excel

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Đoạn chat:\n{chat_text}\n\nLưu ý: Bạn BẮT BUỘC phải xuất kết quả ở dạng JSON thuần túy (không giải thích, không tóm tắt, không phân tích, không thêm bất kỳ chữ nào ngoài JSON). Mẫu:\n{{\n  \"ten\": \"\",\n  \"sdt\": \"\",\n  \"dia_chi\": \"\",\n  \"gia_chot\": \"\",\n  \"ly_do_tinh_so_hop\": \"\",\n  \"so_hop\": \"\"\n}}"}
        ],
        "temperature": 0.1, # Nhiệt độ thấp giúp AI làm theo khuôn rập, không tự sáng tạo thêm
    }

    fallback_delays = [5, 3, 6, 10]
    max_retries = len(fallback_delays)
    
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            result = response.json()
            
            # Lấy nội dung text từ AI
            content = result['choices'][0]['message']['content']
            
            # Dùng Regex để tìm khối JSON phòng khi AI lỡ chèn chữ "Tóm tắt..." vào
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
                    
                # Mặc định lấy thời gian chờ từ mảng [5, 3, 6, 10]
                wait_time = fallback_delays[attempt]
                
                # Nếu API Groq có trả về số giây chính xác (ví dụ 15s), thì ưu tiên dùng số đó để chắc chắn thành công
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

# def main():
#     json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
#     if not json_files:
#         print("Không tìm thấy file JSON nào trong thư mục data.")
#         return

#     import datetime
#     print(f"Tìm thấy {len(json_files)} file lịch sử chat. Bắt đầu dùng AI để phân tích...\n")

#     # Kiểm tra file CSV đã tồn tại chưa
#     csv_mode = 'w'  # Mặc định tạo mới
#     if os.path.exists(OUTPUT_CSV):
#         # Đọc file để kiểm tra có data hay không
#         with open(OUTPUT_CSV, 'r', encoding='utf-8-sig') as check_file:
#             content = check_file.read().strip()
#             # Kiểm tra có dòng data nào không (bỏ qua header và dòng timestamp)
#             lines = [l for l in content.split('\n') if l.strip() and not l.startswith('#')]
#             has_data = len(lines) > 1  # Có nhiều hơn 1 dòng header = có data
        
#         if has_data:
#             print(f"⚠️  File '{os.path.basename(OUTPUT_CSV)}' ĐÃ CÓ DỮ LIỆU!")
#             clear_choice = input("   Bạn có muốn XÓA SẠCH dữ liệu cũ trước khi chạy? (y/N): ").strip().lower()
#             if clear_choice == 'y':
#                 csv_mode = 'w'
#                 print("   → Đã xóa dữ liệu cũ. Bắt đầu ghi mới.\n")
#             else:
#                 csv_mode = 'a'
#                 print("   → Giữ nguyên dữ liệu cũ. Ghi nối thêm vào cuối.\n")
#         else:
#             print(f"File '{os.path.basename(OUTPUT_CSV)}' đã tồn tại nhưng trống. Bắt đầu ghi.\n")
#             csv_mode = 'w'
    
#     # Mở file CSV để ghi kết quả
#     fieldnames = ['File Nguồn', 'Tên Khách Hàng', 'Số Điện Thoại', 'Địa Chỉ', 'Giá Chốt', 'Số Hộp', 'Tổng Tin Nhắn']
#     with open(OUTPUT_CSV, mode=csv_mode, encoding='utf-8-sig', newline='') as csv_file:
#         writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        
#         # Nếu tạo mới (hoặc xóa sạch), ghi timestamp + header
#         if csv_mode == 'w':
#             timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#             csv_file.write(f"# Thời gian chạy tool: {timestamp}\n")
#             writer.writeheader()

#         for file_path in json_files:
#             file_name = os.path.basename(file_path)
#             with open(file_path, 'r', encoding='utf-8') as f:
#                 data = json.load(f)

#             messages = data.get('messages', [])
#             if not messages:
#                 continue

#             # Ghép lịch sử chat lại thành một đoạn văn bản ngắn gọn
#             chat_text = ""
#             for msg in messages:
#                 # Chỉ lấy 1 đoạn hội thoại giới hạn để tiết kiệm token và chạy nhanh hơn
#                 chat_text += f"{msg['sender']}: {msg['content']}\n"
            
#             print(f"Đang phân tích file: {file_name}...", end=" ", flush=True)
#             start_time = time.time()
#             ai_result = extract_info_with_ai(chat_text)
#             elapsed_time = round(time.time() - start_time, 2)
#             print(f"({elapsed_time}s)")
            
#             # Nếu AI không lấy được tên, dùng tạm tên trên Facebook
#             ten_khach = ai_result.get('ten', '').strip()
#             if not ten_khach:
#                 ten_khach = data.get('customerName', '')

#             writer.writerow({
#                 'File Nguồn': file_name,
#                 'Tên Khách Hàng': ten_khach,
#                 'Số Điện Thoại': ai_result.get('sdt', ''),
#                 'Địa Chỉ': ai_result.get('dia_chi', ''),
#                 'Giá Chốt': ai_result.get('gia_chot', ''),
#                 'Số Hộp': ai_result.get('so_hop', ''),
#                 # 'Tổng Tin Nhắn': data.get('totalMessages', 0)
#             })
            
#             print(f" -> Tên: {ten_khach} | SĐT: {ai_result.get('sdt', '')} | Địa chỉ: {ai_result.get('dia_chi', '')} | Giá: {ai_result.get('gia_chot', '')} | Số hộp: {ai_result.get('so_hop', '')}")
            
#             # Nghỉ 5s giữa các request để tránh quá tải API (Rate Limit)
#             time.sleep(5)

#     print(f"\n HOÀN TẤT! Toàn bộ thông tin đã được lưu ra file Excel: {OUTPUT_CSV}")

def main():
    # --- CẬP NHẬT: Loại bỏ các file đã có chữ "done_" ở đầu để không quét lại ---
    all_json = glob.glob(os.path.join(DATA_DIR, "*.json"))
    json_files = [f for f in all_json if not os.path.basename(f).startswith("done_")]
    
    if not json_files:
        print("Không tìm thấy file JSON nào mới (chưa xử lý) trong thư mục data.")
        return

    import datetime
    print(f"Tìm thấy {len(json_files)} file lịch sử chat. Bắt đầu dùng AI để phân tích...\n")

    # Kiểm tra file CSV đã tồn tại chưa
    csv_mode = 'w'  # Mặc định tạo mới
    if os.path.exists(OUTPUT_CSV):
        # Đọc file để kiểm tra có data hay không
        with open(OUTPUT_CSV, 'r', encoding='utf-8-sig') as check_file:
            content = check_file.read().strip()
            # Kiểm tra có dòng data nào không (bỏ qua header và dòng timestamp)
            lines = [l for l in content.split('\n') if l.strip() and not l.startswith('#')]
            has_data = len(lines) > 1  # Có nhiều hơn 1 dòng header = có data
        
        if has_data:
            print(f"⚠️  File '{os.path.basename(OUTPUT_CSV)}' ĐÃ CÓ DỮ LIỆU!")
            clear_choice = input("   Bạn có muốn XÓA SẠCH dữ liệu cũ trước khi chạy? (y/N): ").strip().lower()
            if clear_choice == 'y':
                csv_mode = 'w'
                print("   → Đã xóa dữ liệu cũ. Bắt đầu ghi mới.\n")
            else:
                csv_mode = 'a'
                print("   → Giữ nguyên dữ liệu cũ. Ghi nối thêm vào cuối.\n")
        else:
            print(f"File '{os.path.basename(OUTPUT_CSV)}' đã tồn tại nhưng trống. Bắt đầu ghi.\n")
            csv_mode = 'w'
    
    # Mở file CSV để ghi kết quả
    fieldnames = ['File Nguồn', 'Tên Khách Hàng', 'Số Điện Thoại', 'Địa Chỉ', 'Giá Chốt', 'Số Hộp', 'Tổng Tin Nhắn']
    with open(OUTPUT_CSV, mode=csv_mode, encoding='utf-8-sig', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        
        # Nếu tạo mới (hoặc xóa sạch), ghi timestamp + header
        if csv_mode == 'w':
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

            # Ghép lịch sử chat lại thành một đoạn văn bản ngắn gọn
            chat_text = ""
            for msg in messages:
                # Chỉ lấy 1 đoạn hội thoại giới hạn để tiết kiệm token và chạy nhanh hơn
                chat_text += f"{msg['sender']}: {msg['content']}\n"
            
            print(f"Đang phân tích file: {file_name}...", end=" ", flush=True)
            start_time = time.time()
            ai_result = extract_info_with_ai(chat_text)
            elapsed_time = round(time.time() - start_time, 2)
            print(f"({elapsed_time}s)")
            
            # Nếu AI không lấy được tên, dùng tạm tên trên Facebook
            ten_khach = ai_result.get('ten', '').strip()
            if not ten_khach:
                ten_khach = data.get('customerName', '')

            writer.writerow({
                'File Nguồn': file_name,
                'Tên Khách Hàng': ten_khach,
                'Số Điện Thoại': ai_result.get('sdt', ''),
                'Địa Chỉ': ai_result.get('dia_chi', ''),
                'Giá Chốt': ai_result.get('gia_chot', ''),
                'Số Hộp': ai_result.get('so_hop', ''),
                # 'Tổng Tin Nhắn': data.get('totalMessages', 0)
            })
            
            print(f" -> Tên: {ten_khach} | SĐT: {ai_result.get('sdt', '')} | Địa chỉ: {ai_result.get('dia_chi', '')} | Giá: {ai_result.get('gia_chot', '')} | Số hộp: {ai_result.get('so_hop', '')}")
            
            # --- CẬP NHẬT: Đổi tên file để đánh dấu đã xử lý xong ---
            new_file_name = f"done_{file_name}"
            new_file_path = os.path.join(DATA_DIR, new_file_name)
            try:
                # Phải đóng file trước khi đổi tên (đã đóng ở block 'with' bên trên rồi)
                os.rename(file_path, new_file_path)
                print(f" -> Đã đổi tên thành: {new_file_name}")
            except Exception as e:
                print(f" -> Lỗi khi đổi tên file: {e}")
            # --------------------------------------------------------
            
            # Nghỉ 5s giữa các request để tránh quá tải API (Rate Limit)
            time.sleep(5)

    print(f"\n HOÀN TẤT! Toàn bộ thông tin đã được lưu ra file Excel: {OUTPUT_CSV}")

if __name__ == '__main__':
    main()
