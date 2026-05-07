import asyncio
import logging
import os
from playwright.async_api import async_playwright
import subprocess

# Cấu hình log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEBUG_PORT = 9222
PANCAKE_URL = 'https://pancake.vn/941461145712453'

async def main():
    logger.info("=" * 50)
    logger.info(" BẮT ĐẦU CHẠY TOOL BỎ TAG 'MUA HÀNG' (LỌC THEO 'KIỂM HÀNG')")
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
            logger.info("Tiến hành reload (tải lại) trang web...")
            await page.reload(wait_until='domcontentloaded', timeout=30000)
        
        logger.info("Đang chờ trang tải hoàn tất (5s)...")
        await page.wait_for_timeout(5000)

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
            logger.info("Đã bấm chọn bộ lọc, chờ danh sách cập nhật (3s)...")
            await page.wait_for_timeout(3000)
        elif clicked_filter is False:
            logger.info("Bộ lọc đã được chọn sẵn từ trước.")
        else:
            logger.warning("Không tìm thấy bộ lọc hình vuông trên màn hình.")

        # 2. VÒNG LẶP SCROLL VÀ KIỂM TRA BỎ TAG
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
                    text = await locator.inner_text()
                    await locator.evaluate('el => { const target = el.querySelector(".media-body") || el; target.click(); }')
                    logger.info(f"Đã click vào đoạn chat: {text[:30].replace(chr(10), ' ')}")
                except Exception as e:
                    logger.warning(f"Lỗi khi click đoạn chat {chat_index}: {e}")
                    continue

                # Chờ nội dung chat bên phải load
                await page.wait_for_timeout(2000)

                # KIỂM TRA VÀ BỎ TAG MUA HÀNG
                logger.info("Kiểm tra xem chat có đang gắn tag 'Mua hàng' không...")
                
                # Logic: Nút tag "Mua hàng" đang được chọn sẽ có thẻ <div class="ellipse"></div> bên trong 
                # hoặc màu RGB đậm rgb(13, 90, 255) thay vì rgba(..., 0.4).
                tag_status = await page.evaluate('''() => {
                    const btns = Array.from(document.querySelectorAll('#listShowTags .btn-tag-item'));
                    const muaHangBtn = btns.find(b => b.textContent.trim().toLowerCase() === 'mua hàng');
                    if (muaHangBtn) {
                        // Nút tag đang hoạt động thường có một chấm ellipse bên trong hoặc màu đậm
                        const isActive = muaHangBtn.querySelector('.ellipse') !== null || muaHangBtn.style.backgroundColor.includes('rgb(');
                        if (isActive) {
                            muaHangBtn.click(); // Click để bỏ tag
                            return 'unchecked';
                        }
                        return 'not_active'; // Đã tắt sẵn
                    }
                    return 'not_found';
                }''')
                
                if tag_status == 'unchecked':
                    logger.info("-> Chat ĐANG CÓ tag 'Mua hàng'. Đã tự động TÍCH BỎ TÍCH thành công!")
                    await page.wait_for_timeout(1000) # Chờ 1s để hệ thống lưu trạng thái
                elif tag_status == 'not_active':
                    logger.info("-> Chat KHÔNG CÓ tag 'Mua hàng'. Bỏ qua.")
                else:
                    logger.warning("-> Không tìm thấy nút tag 'Mua hàng' trên giao diện.")

            if new_chats_in_this_view == 0:
                scroll_attempts += 1
                logger.info(f"Không tìm thấy chat mới, đang thử cuộn xuống... (lần {scroll_attempts}/3)")
            else:
                scroll_attempts = 0
                
            # Thực hiện cuộn sidebar xuống dưới
            await page.evaluate('''() => {
                const holder = document.querySelector('.rc-virtual-list-holder');
                if (holder) {
                    holder.scrollTop += 800;
                } else {
                    const fallback = document.querySelector('.conversation-list-item')?.closest('div[style*="overflow"]');
                    if(fallback) fallback.scrollTop += 800;
                }
            }''')
            await page.wait_for_timeout(2000)

        logger.info("=" * 50)
        logger.info(f" HOÀN TẤT! Đã kiểm tra và gỡ tag cho tổng cộng: {chat_index} đoạn chat.")
        logger.info("=" * 50)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
