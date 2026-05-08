@echo off
echo ============================================
echo   MO CHROME VOI PROFILE DEBUG (PORT 9222)
echo ============================================
echo.

:: Kiem tra Chrome co dang chay voi port 9222 khong
netstat -ano | findstr "9222" >NUL
if %ERRORLEVEL%==0 (
    echo [!] Port 9222 dang duoc su dung. Dang dong Chrome cu...
    taskkill /F /IM chrome.exe >NUL 2>&1
    timeout /t 2 /nobreak >NUL
)

echo Dang mo Chrome voi Profile rieng biet...
echo.

:: Su dung profile trong thu muc du an de duoc phep bat Debug port
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="%~dp0chrome_debug_profile" --remote-debugging-port=9222 "https://pancake.vn/941461145712453"

echo [OK] Chrome da mo!
echo.
echo ============================================
echo   HUONG DAN QUAN TRONG:
echo   1. Day la Profile Chrome rieng cho tool.
echo   2. Hay DANG NHAP PANCAKE lai tren Chrome nay (chi can 1 lan).
echo   3. Sau khi dang nhap xong, chay:  node scrape_chat.js
echo ============================================
echo.
pause
