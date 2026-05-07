import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        page = browser.contexts[0].pages[0]
        
        # Click the first tag
        await page.evaluate('''() => {
            document.querySelectorAll('.filter-conversation-tag-tiled .tag-list-item')[0].click();
        }''')
        
        await page.wait_for_timeout(1000)
        
        # Check again
        info = await page.evaluate('''() => {
            const tags = document.querySelectorAll('.filter-conversation-tag-tiled .tag-list-item');
            return Array.from(tags).map(t => ({
                className: t.className,
                bg: t.style.backgroundColor,
                hasSvg: !!t.querySelector('svg'),
                html: t.outerHTML
            }));
        }''')
        
        for i, t in enumerate(info):
            print(f"Tag {i} AFTER CLICK: bg={t['bg']}, class={t['className']}, hasSvg={t['hasSvg']}")
            if i == 0:
                print(f"HTML: {t['html']}")
                
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
