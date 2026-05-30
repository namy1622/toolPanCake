import asyncio
import logging
import json
import os
import datetime
from playwright.async_api import async_playwright

# Constants
DEBUG_PORT = 9222
PAGES = {
    "1": {"name": "Dây Thìa Canh", "url": "https://pancake.vn/571938736002434"},
    "2": {"name": "Trà Đông Trùng", "url": "https://pancake.vn/941461145712453"},
}

print("=" * 50)
print(" CHỌN PAGE CẦN CÀO DỮ LIỆU")
print("=" * 50)
for key, val in PAGES.items():
    print(f" {key}. {val['name']} ({val['url']})")
page_choice = input("\nNhập số thứ tự để chọn (Mặc định 1): ").strip() or "1"
if page_choice not in PAGES:
    page_choice = "1"
PANCAKE_URL = PAGES[page_choice]["url"]
print(f"\n-> Đã chọn page: {PAGES[page_choice]['name']}")
print("-" * 50)

WORKSPACE_DIR = r'F:\tool_cao_data'

# Create folders
today_str = datetime.datetime.now().strftime("%d-%m")
LOG_DIR = os.path.join(WORKSPACE_DIR, 'logs', today_str)
DATA_DIR = os.path.join(WORKSPACE_DIR, 'data')
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

OUTPUT_LOG = os.path.join(LOG_DIR, 'scraper_logs.txt')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(OUTPUT_LOG, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

import subprocess

async def main():
    logger.info("=" * 50)
    logger.info(" BẮT ĐẦU CHẠY TOOL LẤY DỮ LIỆU PANCAKE (V2 - CHỐNG LẶP, CÓ LỌC, SCROLL)")
    logger.info("=" * 50)

    async with async_playwright() as p:
        try:
            logger.info(f"Đang kết nối tới trình duyệt Chrome qua cổng {DEBUG_PORT}...")
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{DEBUG_PORT}")
            logger.info("Kết nối thành công!")
        except Exception as e:
            logger.warning(f"Chưa mở Chrome hoặc lỗi kết nối. Đang tự động gọi lệnh mở Chrome...")
            
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            user_data_dir = r"F:\ToolPancake\chrome_debug_profile"
            
            try:
                # Mở Chrome dưới dạng process độc lập
                subprocess.Popen([
                    chrome_path,
                    f'--user-data-dir={user_data_dir}',
                    f'--remote-debugging-port={DEBUG_PORT}',
                    PANCAKE_URL
                ])
                logger.info("Đã phát lệnh mở Chrome. Vui lòng chờ 5 giây để Chrome khởi động...")
                await asyncio.sleep(5)
                
                # Thử kết nối lại lần 2
                browser = await p.chromium.connect_over_cdp(f"http://localhost:{DEBUG_PORT}")
                logger.info("Kết nối thành công sau khi tự động mở trình duyệt!")
            except Exception as e2:
                logger.error(f"Vẫn không thể kết nối tới Chrome sau khi thử mở. Vui lòng tự mở tay. Chi tiết lỗi: {e2}")
                return

        contexts = browser.contexts
        if not contexts:
            logger.error("Không tìm thấy browser context nào.")
            await browser.close()
            return
        
        context = contexts[0]
        pages = context.pages
        logger.info(f"Đã tìm thấy {len(pages)} tabs đang mở.")

        page = None
        for p_tab in pages:
            if 'pancake.vn' in p_tab.url:
                page = p_tab
                break
        
        if not page:
            logger.info("Không tìm thấy tab Pancake, đang mở tab mới...")
            page = pages[0]
            await page.goto(PANCAKE_URL, wait_until='domcontentloaded', timeout=30000)
        else:
            logger.info(f"Đang dùng tab Pancake hiện tại: {page.url}")
            logger.info("Tiến hành reload (tải lại) trang web...")
            await page.reload(wait_until='domcontentloaded', timeout=30000)
        
        logger.info("Đang chờ trang tải hoàn tất (5s)...")
        await page.wait_for_timeout(5000)

        # 1. BẤM BỘ LỌC ĐẦU TIÊN (HÌNH VUÔNG MÀU XÁM) NẾU CHƯA CHỌN
        logger.info("Kiểm tra bộ lọc (nút hình vuông màu xám)...")
        clicked_filter = await page.evaluate('''() => {
            const tags = document.querySelectorAll('.filter-conversation-tag-tiled .tag-list-item');
            if (tags.length > 0) {
                const firstTag = tags[0];
                // Khi đã chọn, nó sẽ chuyển sang màu đậm hơn (thường là rgb(75, 85, 119))
                if (firstTag.style.backgroundColor !== 'rgb(75, 85, 119)') {
                    firstTag.click();
                    return true; // đã click
                }
                return false; // đã được chọn từ trước
            }
            return null; // không tìm thấy nút này
        }''')
        
        if clicked_filter is True:
            logger.info("Đã bấm chọn bộ lọc, chờ danh sách cập nhật (3s)...")
            await page.wait_for_timeout(3000)
        elif clicked_filter is False:
            logger.info("Bộ lọc đã được chọn sẵn từ trước.")
        else:
            logger.warning("Không tìm thấy bộ lọc hình vuông trên màn hình.")

        # 2. VÒNG LẶP SCROLL ĐỂ LẤY TOÀN BỘ CHAT
        logger.info("Bắt đầu quét danh sách đoạn chat trên sidebar...")
        
        processed_chat_ids = set()
        scroll_attempts = 0
        chat_index = 0

        while scroll_attempts < 3:
            chat_locators = page.locator('.conversation-list-item')
            count = await chat_locators.count()
            
            new_chats_in_this_view = 0
            
            for i in range(count):
                locator = chat_locators.nth(i)
                
                try:
                    chat_id = await locator.get_attribute('id')
                except Exception:
                    continue
                    
                if not chat_id or chat_id in processed_chat_ids:
                    continue
                    
                processed_chat_ids.add(chat_id)
                new_chats_in_this_view += 1
                chat_index += 1
                
                logger.info(f"--- Đang xử lý chat thứ {chat_index} ---")
                
                try:
                    # Lấy text ngắn để hiển thị log trước
                    text = await locator.inner_text()
                    
                    # Dùng JS click thẳng vào DOM để không tự động cuộn (tránh làm hỏng index của danh sách ảo)
                    await locator.evaluate('el => { const target = el.querySelector(".media-body") || el; target.click(); }')
                    
                    logger.info(f"Đã click vào đoạn chat: {text[:30].replace(chr(10), ' ')}")
                except Exception as e:
                    logger.warning(f"Lỗi khi click đoạn chat {chat_index}: {e}")
                    continue

                # Chờ chat load trên giao diện chính
                logger.info("Chờ nội dung chat load (2s)...")
                await page.wait_for_timeout(2000)

                # 3. TRÍCH XUẤT DỮ LIỆU (CHỐNG LẶP & ĐÚNG NGƯỜI GỬI)
                logger.info("Đang trích xuất dữ liệu chat...")
                chat_info = await page.evaluate('''() => {
                    let customerName = 'Unknown';
                    const headerSelectors = [
                        '[class*="customer-name"]', '[class*="contact-name"]',
                        '[class*="user-name"]', '[class*="userName"]',
                        '[class*="header"] h3', '[class*="header"] h4',
                        '[class*="header"] span', '[class*="name"]',
                        '[class*="title"]',
                    ];
                    for (const sel of headerSelectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            const t = el.innerText?.trim();
                            if (t && t.length > 1 && t.length < 100 && t !== 'Xin chọn 1 hội thoại') {
                                customerName = t;
                                break;
                            }
                        }
                    }

                    // Chỉ lấy các thẻ có class "inbox-message-ele" để tránh bị lặp nội dung
                    const messageEls = document.querySelectorAll('.inbox-message-ele');

                    const messages = Array.from(messageEls).map((el, i) => {
                        const cls = String(el.getAttribute('class') || '').toLowerCase();
                        
                        let sender = customerName; // Mặc định là tên khách hàng
                        // Phân biệt người gửi chính xác dựa vào class của Pancake
                        if (cls.includes('media-current-user')) {
                            sender = 'Tôi';
                        } else if (cls.includes('media-current-customer')) {
                            sender = customerName;
                        }
                        
                        const text = el.innerText?.trim() || '';
                        return {
                            sender: sender,
                            content: text
                        };
                    }).filter(m => m.content.length > 0);

                    return {
                        customerName,
                        messages
                    };
                }''')

                customer_name = chat_info.get('customerName', 'Unknown')
                messages = chat_info.get('messages', [])

                logger.info(f"Tên khách hàng: {customer_name}")
                logger.info(f"Số lượng tin nhắn lấy được: {len(messages)}")

                # Lưu vào file JSON riêng biệt cho mỗi đoạn chat
                output_data = {
                    "scrapedAt": datetime.datetime.now().isoformat(),
                    "customerName": customer_name,
                    "url": page.url,
                    "totalMessages": len(messages),
                    "messages": messages
                }

                # Tên file an toàn (bỏ các ký tự đặc biệt)
                safe_name = "".join([c for c in customer_name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                if not safe_name: safe_name = f"chat_{chat_index}"
                
                json_filename = os.path.join(DATA_DIR, f"{chat_index}_{safe_name}_{today_str}.json")
                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)

                logger.info(f"Đã lưu JSON tại: {json_filename}")

                # BẤM TAG "Mua hàng" SAU KHI LẤY DATA
                logger.info("Đang gắn tag 'Mua hàng'...")
                clicked_tag = await page.evaluate('''() => {
                    const btns = Array.from(document.querySelectorAll('#listShowTags .btn-tag-item'));
                    const muaHangBtn = btns.find(b => b.textContent.trim().toLowerCase() === 'mua hàng');
                    if (muaHangBtn) {
                        muaHangBtn.click();
                        return true;
                    }
                    return false;
                }''')
                
                if clicked_tag:
                    logger.info("Đã bấm gắn tag 'Mua hàng' thành công.")
                    await page.wait_for_timeout(1500) # Đợi 1s để hệ thống lưu tag trước khi sang chat khác
                else:
                    logger.warning("Không tìm thấy nút tag 'Mua hàng' trên giao diện.")

            if new_chats_in_this_view == 0:
                # Nếu không tìm thấy chat mới nào trên màn hình, thử cuộn xuống và đếm số lần thử
                scroll_attempts += 1
                logger.info(f"Không tìm thấy chat mới, đang thử cuộn xuống... (lần {scroll_attempts}/3)")
            else:
                # Reset số lần cuộn vì vừa tìm thấy thêm chat mới
                scroll_attempts = 0
                
            # Thực hiện cuộn sidebar xuống dưới
            await page.evaluate('''() => {
                const holder = document.querySelector('.rc-virtual-list-holder');
                if (holder) {
                    holder.scrollTop += 800; // Cuộn xuống khoảng 1 trang
                } else {
                    const fallback = document.querySelector('.conversation-list-item')?.closest('div[style*="overflow"]');
                    if(fallback) fallback.scrollTop += 800;
                }
            }''')
            # Đợi cho danh sách ảo render các phần tử mới
            await page.wait_for_timeout(1500)

        logger.info("=" * 50)
        logger.info(f" HOÀN TẤT QUÉT TẤT CẢ ĐOẠN CHAT! Tổng số: {chat_index}")
        logger.info("=" * 50)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
