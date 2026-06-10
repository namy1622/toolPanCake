"""
Module trích xuất Tỉnh/Thành, Quận/Huyện, Phường/Xã từ chuỗi địa chỉ bằng AI.
File riêng biệt chứa system prompt và hàm gọi API.
"""
import re
import json
import time
import requests

# ── System Prompt: Phân tích địa chỉ → Tỉnh / Huyện / Xã ──
SYSTEM_PROMPT_EXTRACT_ADDRESS = """Bạn là trợ lý phân tích địa chỉ giao hàng tại Việt Nam. 
Nhiệm vụ: Từ một chuỗi địa chỉ bất kỳ (có thể viết tắt, không dấu, sai chính tả), hãy xác định và trả về:
- "tinh": Tên Tỉnh hoặc Thành phố (viết đầy đủ có dấu, ví dụ: "Hà Nội", "TP.Hồ Chí Minh", "Đắk Lắk", "Thanh Hóa")
- "huyen": Tên Quận hoặc Huyện hoặc Thị xã hoặc Thành phố thuộc tỉnh (viết đầy đủ có dấu, ví dụ: "Quận 1", "Huyện Bình Chánh", "Thị xã Phú Mỹ", "Thành phố Thanh Hóa")
- "xa": Tên Phường hoặc Xã hoặc Thị trấn (viết đầy đủ có dấu, ví dụ: "Phường Bến Nghé", "Xã Tân Kiên", "Thị trấn Củ Chi")

QUY TẮC:
1. Phải trả về tên ĐẦY ĐỦ CÓ DẤU của các đơn vị hành chính Việt Nam.
2. Nếu địa chỉ viết tắt (ví dụ: "q1" → "Quận 1", "tp hcm" → "Hồ Chí Minh", "bình dương" → "Bình Dương"), bạn phải suy luận ra tên đầy đủ.
3. Nếu KHÔNG XÁC ĐỊNH ĐƯỢC thì để chuỗi rỗng "".
4. KHÔNG bịa ra địa danh không tồn tại.

--- VÍ DỤ ---
Địa chỉ: "123 le loi q1 tp hcm"
→ {"tinh": "Hồ Chí Minh", "huyen": "Quận 1", "xa": ""}

Địa chỉ: "xã tân phú, huyện đồng phú, bình phước"
→ {"tinh": "Bình Phước", "huyen": "Huyện Đồng Phú", "xa": "Xã Tân Phú"}

Địa chỉ: "số 5 ngõ 12 đường láng, đống đa, hà nội"
→ {"tinh": "Hà Nội", "huyen": "Quận Đống Đa", "xa": ""}

--- KẾT QUẢ TRẢ VỀ ---
Chỉ trả về 1 khối JSON duy nhất, không có giải thích nào khác:
{
  "tinh": "",
  "huyen": "",
  "xa": ""
}
"""

# Kết quả rỗng mặc định khi lỗi
EMPTY_ADDRESS_RESULT = {"tinh": "", "huyen": "", "xa": ""}


def extract_address_with_ai(address, api_key, api_url, model):
    """
    Gọi API AI để phân tích địa chỉ → trích xuất Tỉnh/Huyện/Xã.
    
    Args:
        address: Chuỗi địa chỉ gốc từ đoạn chat
        api_key: API key cho dịch vụ AI
        api_url: URL endpoint API
        model: Tên model AI
    
    Returns:
        dict: {tinh, huyen, xa}
    """
    if not address or address.strip() == '':
        return dict(EMPTY_ADDRESS_RESULT)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_EXTRACT_ADDRESS},
            {"role": "user", "content": f"Địa chỉ: \"{address}\"\n\nChỉ trả về JSON thuần túy, không giải thích:\n{{\n  \"tinh\": \"\",\n  \"huyen\": \"\",\n  \"xa\": \"\"\n}}"}
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
                return dict(EMPTY_ADDRESS_RESULT)
                
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
                
                print(f"\n [!] Quá tải API (address). Đang chờ {wait_time:.1f}s để thử lại (Lần {attempt+1}/{max_retries})...", end=" ", flush=True)
                time.sleep(wait_time)
                continue
            else:
                print(f"\nLỗi khi gọi API (address): {e}")
                if 'response' in locals() and hasattr(response, 'text'):
                    print(f"Chi tiết response: {response.text}")
                return dict(EMPTY_ADDRESS_RESULT)
        except Exception as e:
            print(f"\nLỗi khi gọi API (address): {e}")
            if 'response' in locals() and hasattr(response, 'text'):
                print(f"Chi tiết response: {response.text}")
            return dict(EMPTY_ADDRESS_RESULT)
            
    print(f"\n [!] Bỏ cuộc trích xuất địa chỉ sau {max_retries} lần thử. Bỏ qua.")
    return dict(EMPTY_ADDRESS_RESULT)
