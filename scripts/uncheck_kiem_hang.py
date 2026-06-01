import asyncio
import logging
import os
import sys
from playwright.async_api import async_playwright
import subprocess

# Đảm bảo luồng xuất dữ liệu luôn dùng UTF-8 trên Windows để tránh lỗi CP1252
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Cấu hình log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEBUG_PORT = 9222

# Tự động xác định thư mục gốc của dự án
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(SCRIPT_DIR) == 'scripts':
    WORKSPACE_DIR = os.path.dirname(SCRIPT_DIR)
else:
    WORKSPACE_DIR = SCRIPT_DIR

# Danh sách page
PAGES = {
    "1": {"name": "Dây Thìa Canh", "url": "https://pancake.vn/571938736002434"},
    "2": {"name": "Trà Đông Trùng", "url": "https://pancake.vn/941461145712453"},
}

# Nhận tham số dòng lệnh cho page_choice
if len(sys.argv) > 1:
    page_choice = sys.argv[1].strip()
    print(f"Nhận tham số dòng lệnh page: {page_choice}")
else:
    print("=" * 50)
    print(" CHỌN PAGE CẦN BỎ TAG 'KIỂM HÀNG'")
    print("=" * 50)
    for key, val in PAGES.items():
        print(f" {key}. {val['name']} ({val['url']})")
    page_choice = input("\nNhập số thứ tự để chọn (Mặc định 1): ").strip() or "1"

if page_choice not in PAGES:
    page_choice = "1"
selected_page = PAGES[page_choice]
PANCAKE_URL = selected_page["url"]
print(f"\n-> Đã chọn page: {selected_page['name']}")
print("-" * 50)

async def main():
    logger.info("=" * 50)
    logger.info(" BẮT ĐẦU CHẠY TOOL BỎ TAG 'KIỂM HÀNG' (ĐIỀU KIỆN: CÓ CẢ TAG MUA HÀNG)")
    logger.info("=" * 50)

    async with async_playwright() as p:
        try:
            logger.info(f"Đang kết nối tới trình duyệt Chrome qua cổng {DEBUG_PORT}...")
            browser = await p.chromium.connect_over_cdp(f"http://localhost:{DEBUG_PORT}")
            logger.info("Kết nối thành công!")
        except Exception as e:
            logger.warning(f"Chưa mở Chrome hoặc lỗi kết nối. Đang tự động gọi lệnh mở Chrome...")
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            user_data_dir = os.path.join(WORKSPACE_DIR, "chrome_debug_profile")
            try:
                subprocess.Popen([
                    chrome_path,
                    f'--user-data-dir={user_data_dir}',
                    f'--remote-debugging-port={DEBUG_PORT}',
                    PANCAKE_URL
                ])
                logger.info("Đã phát lệnh mở Chrome. Vui lòng chờ 5 giây để Chrome khởi động...")
                await asyncio.sleep(5)
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
            if PANCAKE_URL not in page.url:
                logger.info(f"Tab hiện tại KHÁC page đã chọn → Điều hướng tới: {PANCAKE_URL}")
                await page.goto(PANCAKE_URL, wait_until='domcontentloaded', timeout=30000)
            else:
                logger.info("Tab đúng page đã chọn → Tiến hành reload (tải lại) trang web...")
                await page.reload(wait_until='domcontentloaded', timeout=30000)
        
        logger.info("Đang chờ trang tải hoàn tất (3s)...")
        await page.wait_for_timeout(3000)

        # 1. BẤM BỘ LỌC ĐẦU TIÊN (HÌNH VUÔNG MÀU XÁM - KIỂM HÀNG) NẾU CHƯA CHỌN
        logger.info("Kiểm tra bộ lọc (nút hình vuông màu xám)...")
        clicked_filter = await page.evaluate('''() => {
            const tags = document.querySelectorAll('.filter-conversation-tag-tiled .tag-list-item');
            if (tags.length > 0) {
                const firstTag = tags[0];
                if (firstTag.style.backgroundColor !== 'rgb(75, 85, 119)') {
                    firstTag.click();
                    return true; // đã click
                }
                return false; // đã được chọn từ trước
            }
            return null; // không tìm thấy nút này
        }''')
        
        if clicked_filter is True:
            logger.info("Đã bấm chọn bộ lọc, chờ danh sách cập nhật (2s)...")
            await page.wait_for_timeout(2000)
        elif clicked_filter is False:
            logger.info("Bộ lọc đã được chọn sẵn từ trước.")
        else:
            logger.warning("Không tìm thấy bộ lọc hình vuông trên màn hình.")

        # 2. VÒNG LẶP XỬ LÝ TỪNG CHAT TRÊN SIDEBAR
        logger.info("Bắt đầu quét danh sách đoạn chat trên sidebar...")
        
        chat_index = 0
        unchecked_count = 0
        skipped_count = 0
        no_more_chat_attempts = 0
        skip_offset = 0

        while no_more_chat_attempts < 3:
            chat_locators = page.locator('.conversation-list-item')
            count = await chat_locators.count()
            
            if skip_offset >= count:
                no_more_chat_attempts += 1
                logger.info(f"Đã hết chat trong tầm nhìn. Thử cuộn xuống... (lần {no_more_chat_attempts}/3)")
                await page.evaluate('''() => {
                    const holder = document.querySelector('.rc-virtual-list-holder');
                    if (holder) holder.scrollTop += 800;
                }''')
                await page.wait_for_timeout(2000)
                continue
            
            no_more_chat_attempts = 0
            chat_index += 1
            
            # Click vào chat ở vị trí skip_offset
            target_chat = chat_locators.nth(skip_offset)
            try:
                text = await target_chat.inner_text()
                await target_chat.evaluate('el => { const target = el.querySelector(".media-body") || el; target.click(); }')
                logger.info(f"--- Chat thứ {chat_index}: {text[:40].replace(chr(10), ' ')} ---")
            except Exception as e:
                logger.warning(f"Lỗi khi click đoạn chat {chat_index}: {e}")
                break

            # Chờ nội dung chat bên phải load
            await page.wait_for_timeout(800)

            # KIỂM TRA TAG VÀ QUYẾT ĐỊNH BỎ TÍCH HAY BỎ QUA
            logger.info("Kiểm tra điều kiện tag...")
            
            tag_status = await page.evaluate('''() => {
                const btns = Array.from(document.querySelectorAll('#listShowTags .btn-tag-item'));
                
                const isActive = (btn) => {
                    if (!btn) return false;
                    if (btn.querySelector('.ellipse') !== null) return true;
                    const bg = btn.style.backgroundColor || '';
                    if (bg.includes('rgba') && bg.includes('0.4')) return false;
                    if (bg.includes('rgb')) return true;
                    return false;
                };
                
                const activeTags = btns.filter(b => isActive(b));
                const activeTagNames = activeTags.map(b => b.textContent.trim().toLowerCase());
                
                const hasMuaHang = activeTagNames.includes('mua hàng');
                const hasKiemHang = activeTagNames.includes('kiểm hàng');
                
                if (hasMuaHang && hasKiemHang && activeTags.length === 2) {
                    const kiemHangBtn = btns.find(b => b.textContent.trim().toLowerCase() === 'kiểm hàng');
                    kiemHangBtn.click();
                    return 'unchecked';
                }
                
                if (hasKiemHang && !hasMuaHang) return 'skip_only_kiem';
                if (hasMuaHang && hasKiemHang && activeTags.length > 2) return 'skip_extra_tags';
                if (!hasKiemHang) return 'skip_no_kiem';
                return 'skip_unknown';
            }''')
            
            if tag_status == 'unchecked':
                unchecked_count += 1
                logger.info(f"✅ Đã BỎ TÍCH 'Kiểm hàng' thành công! (Tổng: {unchecked_count})")
            else:
                skipped_count += 1
                
                if tag_status == 'skip_only_kiem':
                    logger.info(f"⏭️ BỎ QUA - Chỉ có tag 'Kiểm hàng' (không có 'Mua hàng'). (Bỏ qua: {skipped_count})")
                elif tag_status == 'skip_extra_tags':
                    logger.info(f"⏭️ BỎ QUA - Có tag ngoài 'Mua hàng' và 'Kiểm hàng'. (Bỏ qua: {skipped_count})")
                elif tag_status == 'skip_no_kiem':
                    logger.info(f"⏭️ BỎ QUA - Không có tag 'Kiểm hàng'. (Bỏ qua: {skipped_count})")
                else:
                    logger.info(f"⏭️ BỎ QUA - Trạng thái không xác định. (Bỏ qua: {skipped_count})")
                
                skip_offset += 1

        logger.info("=" * 50)
        logger.info(f" HOÀN TẤT!")
        logger.info(f"   - Đã xử lý: {chat_index} đoạn chat")
        logger.info(f"   - Đã bỏ tích 'Kiểm hàng': {unchecked_count}")
        logger.info(f"   - Đã bỏ qua: {skipped_count}")
        logger.info("=" * 50)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
