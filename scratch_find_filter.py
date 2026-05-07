import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        page = browser.contexts[0].pages[0]
        
        # Lấy HTML của vùng header (tìm kiếm, filter)
        html = await page.evaluate('''() => {
            const searchBox = document.querySelector('input[placeholder*="Tìm kiếm"], input[type="search"]');
            if (searchBox) {
                const parent = searchBox.closest('div.flex, div.row, div.header') || searchBox.parentElement.parentElement;
                return parent.outerHTML;
            }
            return "Not found";
        }''')
        
        with open("F:\\tool_cao_data\\filter_html.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
