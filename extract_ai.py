import os
import json
import requests
import csv
import glob
import sys
import re

# Cấu hình đường dẫn
WORKSPACE_DIR = r"F:\tool_cao_data"

# Đọc cấu hình từ appsettings.json
SETTINGS_FILE = os.path.join(WORKSPACE_DIR, "appsettings.json")
try:
    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
        settings = json.load(f)
        ai_settings = settings.get("AI", {})
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
3. TUYỆT ĐỐI KHÔNG sửa lỗi chính tả, không tự thêm/bớt từ (như phường, xã, quận, huyện).
4. KHÔNG tự suy luận địa danh (thấy "đông anh" không được tự đoán là Hà Nội).
5. ĐỊNH DẠNG SỐ HỘP: Nếu khách chốt 1 hộp thì ghi là "1h", 2 hộp là "2h", 3 hộp là "3h", v.v...

--- VÍ DỤ 1 ---
Khách: gui ve dia chi 123 le loi q1 nhe e 0901234567. minh lay 2 hop nhe, 
Thì Tôi (Người bán) cuối cùng sẽ chốt số hộp và số tiền: Ví dụ như {
      "sender": "Tôi",
      "content": "3 hộp là 240k miễn ship\nMua 3 tặng 1 ( tổng nhận 4 hộp )",
      "class": "media m-b-md inbox-message-ele media-current-user not-same-from-top-mes"
    }, hoặc     {
      "sender": "Tôi",
      "content": "đơn của mình 2 hộp là 160k miễn ship",
      "class": "media m-b-md inbox-message-ele media-current-user not-same-from-top-mes"
    }, thì tương ứng 
    Assistant:
{
  "ten": "",
  "sdt": "0901234567",
  "dia_chi": "123 le loi q1",
  "gia_chot": "240000",
  "so_hop": "4h"
}
hoặc 
Assistant:
{
  "ten": "",
  "sdt": "0901234567",
  "dia_chi": "123 le loi q1",
  "gia_chot": "160000",
  "so_hop": "2h"
}

--- VÍ DỤ 2 ---
Khách: Lê Xuân mình khu phố đông anh 2 thị trấn nam ban lâm hà lâm đồng 0986527800. cho 3 thoi nhe
Thì khi đó vẫn chưa phải là chốt về số hộp  mà chốt phải là "Tôi"ví cụ như {
      "sender": "Tôi",
      "content": "3 hộp là 240k miễn ship\nMua 3 tặng 1 ( tổng nhận 4 hộp )",
      "class": "media m-b-md inbox-message-ele media-current-user not-same-from-top-mes"
    }, thì khi đó chốt là 4h vì mua tặng 1 là 4 hộp 
Assistant:
{
  "ten": "Lê Xuân",
  "sdt": "0986527800",
  "dia_chi": "khu phố đông anh 2 thị trấn nam ban lâm hà lâm đồng",
  "gia_chot": "240000",
  "so_hop": "4h"
}
--- KẾT QUẢ TRẢ VỀ ---
Chỉ trả về 1 khối JSON duy nhất, không có giải thích nào khác:
{
  "ten": "",
  "sdt": "",
  "dia_chi": "",
  "gia_chot": "",
  "so_hop": ""
}"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Đoạn chat:\n{chat_text}\n\nLưu ý: Bạn BẮT BUỘC phải xuất kết quả ở dạng JSON thuần túy (không giải thích, không tóm tắt, không phân tích, không thêm bất kỳ chữ nào ngoài JSON). Mẫu:\n{{\n  \"ten\": \"\",\n  \"sdt\": \"\",\n  \"dia_chi\": \"\",\n  \"gia_chot\": \"\",\n  \"so_hop\": \"\"\n}}"}
        ],
        "temperature": 0.1, # Nhiệt độ thấp giúp AI làm theo khuôn rập, không tự sáng tạo thêm
    }

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
            return {"ten": "", "sdt": "", "dia_chi": "", "gia_chot": "", "so_hop": ""}
            
    except Exception as e:
        print(f"Lỗi khi gọi API: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"Chi tiết response: {response.text}")
        return {"ten": "", "sdt": "", "dia_chi": "", "gia_chot": "", "so_hop": ""}

def main():
    json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    if not json_files:
        print("Không tìm thấy file JSON nào trong thư mục data.")
        return

    print(f"Tìm thấy {len(json_files)} file lịch sử chat. Bắt đầu dùng AI để phân tích...\n")

    # Mở file CSV để ghi kết quả
    with open(OUTPUT_CSV, mode='w', encoding='utf-8-sig', newline='') as csv_file:
        fieldnames = ['File Nguồn', 'Tên Khách Hàng', 'Số Điện Thoại', 'Địa Chỉ', 'Giá Chốt', 'Số Hộp', 'Tổng Tin Nhắn']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
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
            
            print(f"Đang phân tích file: {file_name}...")
            ai_result = extract_info_with_ai(chat_text)
            
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
            
            print(f" -> Tên: {ten_khach} | SĐT: {ai_result.get('sdt', '')} | Địa chỉ: {ai_result.get('dia_chi', '')} | Giá: {ai_result.get('gia_chot', '')} | Số hộp: {ai_result.get('so_hop', '')}h")

    print(f"\n HOÀN TẤT! Toàn bộ thông tin đã được lưu ra file Excel: {OUTPUT_CSV}")

if __name__ == '__main__':
    main()
