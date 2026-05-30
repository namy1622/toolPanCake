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
        # LOGIC QUAN TRỌNG:
        # - Khi bỏ tích "Kiểm hàng" thành công → chat đó BIẾN MẤT khỏi sidebar (vì không còn khớp bộ lọc)
        #   → sidebar TỰ ĐỘNG chọn chat tiếp theo → KHÔNG cần click thêm gì.
        # - Khi BỎ QUA (skip) chat → chat đó VẪN CÒN trên sidebar → phải TỰ TAY click chat tiếp theo bên dưới.
        logger.info("Bắt đầu quét danh sách đoạn chat trên sidebar...")
        
        chat_index = 0
        unchecked_count = 0
        skipped_count = 0
        no_more_chat_attempts = 0
        # skip_offset: Số chat đã bỏ qua (vẫn còn trên sidebar).
        # Dùng để biết cần click vào chat ở vị trí nào.
        # Ví dụ: skip_offset=0 → click chat đầu tiên (index 0)
        #         skip_offset=2 → đã bỏ qua 2 chat phía trên, click chat ở index 2
        skip_offset = 0

        while no_more_chat_attempts < 3:
            # Lấy danh sách chat hiện tại trên sidebar
            chat_locators = page.locator('.conversation-list-item')
            count = await chat_locators.count()
            
            # Kiểm tra xem còn chat nào ở vị trí skip_offset không
            if skip_offset >= count:
                # Đã hết chat trong tầm nhìn, thử cuộn xuống
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
                
                // Đếm tổng số tag đang active
                const activeTags = btns.filter(b => isActive(b));
                const activeTagNames = activeTags.map(b => b.textContent.trim().toLowerCase());
                
                // Tìm 2 tag cần kiểm tra
                const hasMuaHang = activeTagNames.includes('mua hàng');
                const hasKiemHang = activeTagNames.includes('kiểm hàng');
                
                // CHỈ bỏ tích khi có ĐÚNG 2 tag active là "Mua hàng" + "Kiểm hàng"
                if (hasMuaHang && hasKiemHang && activeTags.length === 2) {
                    const kiemHangBtn = btns.find(b => b.textContent.trim().toLowerCase() === 'kiểm hàng');
                    kiemHangBtn.click();
                    return 'unchecked';
                }
                
                // Các trường hợp bỏ qua
                if (hasKiemHang && !hasMuaHang) return 'skip_only_kiem';
                if (hasMuaHang && hasKiemHang && activeTags.length > 2) return 'skip_extra_tags';
                if (!hasKiemHang) return 'skip_no_kiem';
                return 'skip_unknown';
            }''')
            
            if tag_status == 'unchecked':
                unchecked_count += 1
                logger.info(f"✅ Đã BỎ TÍCH 'Kiểm hàng' thành công! (Tổng: {unchecked_count})")
                # SAU KHI BỎ TÍCH: Chờ cho đến khi chat THẬT SỰ biến mất khỏi sidebar
                # (tránh lỗi vòng lặp tiếp theo click lại chat cũ vì nó chưa kịp biến mất)
                # count_before = count
                # for wait_i in range(10):  # Tối đa chờ 5 giây (10 x 500ms)
                #     await page.wait_for_timeout(500)
                #     new_count = await page.locator('.conversation-list-item').count()
                #     if new_count < count_before:
                #         logger.info(f"   Sidebar đã cập nhật ({count_before} → {new_count} chat).")
                #         break
                # else:
                #     logger.warning("   Sidebar chưa cập nhật sau 5s, tiếp tục...")
                
            else:
                # BỎ QUA: Chat vẫn còn trên sidebar.
                # → Tăng skip_offset để lần sau nhảy qua chat này, click chat ở vị trí tiếp theo.
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
