"""
Module trích xuất thông tin khách hàng từ đoạn chat bằng AI.
Chứa system prompt quy tắc tối thượng và hàm gọi API.
"""
import re
import json
import time
import requests

# ── System Prompt: Quy tắc trích xuất thông tin khách hàng ──
SYSTEM_PROMPT_EXTRACT_INFO = """Bạn là trợ lý trích xuất thông tin khách hàng từ đoạn chat mua hàng. Nhiệm vụ: Tìm và trích xuất Tên khách hàng, Số điện thoại, Địa chỉ, Giá chốt cuối cùng, và Số hộp.
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

# Kết quả rỗng mặc định khi lỗi
EMPTY_INFO_RESULT = {
    "ten": "", "sdt": "", "dia_chi": "",
    "gia_chot": "", "ly_do_tinh_so_hop": "", "so_hop": ""
}


def extract_info_with_ai(chat_text, api_key, api_url, model):
    """
    Gọi API AI để trích xuất thông tin khách hàng từ đoạn chat.
    
    Args:
        chat_text: Nội dung đoạn chat dạng text
        api_key: API key cho dịch vụ AI
        api_url: URL endpoint API
        model: Tên model AI
    
    Returns:
        dict: {ten, sdt, dia_chi, gia_chot, ly_do_tinh_so_hop, so_hop}
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_EXTRACT_INFO},
            {"role": "user", "content": f"Đoạn chat:\n{chat_text}\n\nLưu ý: Bạn BẮT BUỘC phải xuất kết quả ở dạng JSON thuần túy (không giải thích, không tóm tắt, không phân tích, không thêm bất kỳ chữ nào ngoài JSON). Mẫu:\n{{\n  \"ten\": \"\",\n  \"sdt\": \"\",\n  \"dia_chi\": \"\",\n  \"gia_chot\": \"\",\n  \"ly_do_tinh_so_hop\": \"\",\n  \"so_hop\": \"\"\n}}"}
        ],
        "temperature": 0.1,
    }

    fallback_delays = [5, 3, 6, 10]
    max_retries = len(fallback_delays)
    
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=90)
            response.raise_for_status()
            result = response.json()
            
            content = result['choices'][0]['message']['content']
            
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                json_str = match.group(0)
                return json.loads(json_str)
            else:
                return dict(EMPTY_INFO_RESULT)
                
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
                
                print(f"\n [!] Quá tải API (info). Đang chờ {wait_time:.1f}s để thử lại (Lần {attempt+1}/{max_retries})...", end=" ", flush=True)
                time.sleep(wait_time)
                continue
            else:
                print(f"\nLỗi khi gọi API (info): {e}")
                if 'response' in locals() and hasattr(response, 'text'):
                    print(f"Chi tiết response: {response.text}")
                return dict(EMPTY_INFO_RESULT)
        except Exception as e:
            print(f"\nLỗi khi gọi API (info): {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                print(f"Chi tiết response: {response.text}")
            return dict(EMPTY_INFO_RESULT)
            
    print(f"\n [!] Bỏ cuộc trích xuất info sau {max_retries} lần thử. Bỏ qua.")
    return dict(EMPTY_INFO_RESULT)
