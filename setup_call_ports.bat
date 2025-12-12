@echo off
echo === Chat P2P - Call Ports Setup (UDP) ===
echo Opening UDP ports 56000-57000 for audio/video calls
echo.

REM Check if running as Administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Please run as Administrator!
    echo Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

echo Opening Windows Firewall for Call Ports...
echo.

REM Add inbound rule for UDP (calls)
netsh advfirewall firewall add rule name="Chat P2P - Calls UDP" dir=in action=allow protocol=UDP localport=56000-57000 profile=private,domain

REM Add outbound rule
netsh advfirewall firewall add rule name="Chat P2P - Calls UDP Out" dir=out action=allow protocol=UDP localport=56000-57000 profile=private,domain

echo.
echo === Setup Complete! ===
echo UDP ports 56000-57000 are now open for calls
echo.
echo Note: TCP port 55000-55199 should also be open for messages
echo Run setup_firewall.bat if not done already
echo.
pause

