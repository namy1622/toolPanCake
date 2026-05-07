import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        page = browser.contexts[0].pages[0]
        
        # In ra các tag list item và class của chúng
        info = await page.evaluate('''() => {
            const tags = document.querySelectorAll('.filter-conversation-tag-tiled .tag-list-item');
            return Array.from(tags).map(t => ({
                className: t.className,
                bg: t.style.backgroundColor,
                border: t.style.border,
                hasSvg: !!t.querySelector('svg'),
                html: t.outerHTML
            }));
        }''')
        
        for i, t in enumerate(info):
            print(f"Tag {i}: {t['bg']}, class: {t['className']}, border: {t['border']}, hasSvg: {t['hasSvg']}")
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
