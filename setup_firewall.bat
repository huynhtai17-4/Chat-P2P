@echo off
echo === Chat P2P - Firewall Setup for Windows ===
echo.

REM Check if running as Administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Please run as Administrator!
    echo Right-click this file and select "Run as administrator"
    pause
    exit /b 1
)

echo Opening Windows Firewall for Chat P2P...
echo.

REM Add inbound rule for TCP
netsh advfirewall firewall add rule name="Chat P2P - TCP" dir=in action=allow protocol=TCP localport=55000-55199 profile=private,domain

REM Add inbound rule for UDP (for calls)
netsh advfirewall firewall add rule name="Chat P2P - UDP" dir=in action=allow protocol=UDP localport=55000-55199 profile=private,domain

REM Add outbound rules
netsh advfirewall firewall add rule name="Chat P2P - TCP Out" dir=out action=allow protocol=TCP localport=55000-55199 profile=private,domain
netsh advfirewall firewall add rule name="Chat P2P - UDP Out" dir=out action=allow protocol=UDP localport=55000-55199 profile=private,domain

echo.
echo === Setup Complete! ===
echo Ports 55000-55199 (TCP/UDP) are now open for Chat P2P
echo.
echo To check firewall rules:
echo   netsh advfirewall firewall show rule name="Chat P2P - TCP"
echo.
pause

