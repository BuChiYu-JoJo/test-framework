@echo off
chcp 65001 >nul
echo ============================================
echo  Claude 数据目录迁移收尾脚本
echo  请在关闭所有 Claude 窗口后运行本脚本
echo  需要以【管理员身份】运行
echo ============================================
echo.

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 请右键此脚本，选择"以管理员身份运行"！
    pause
    exit /b 1
)

:: 检查 Claude 进程
tasklist /FI "IMAGENAME eq Claude.exe" 2>nul | find /I "Claude.exe" >nul
if %errorlevel% equ 0 (
    echo [ERROR] 检测到 Claude Desktop 仍在运行，请先关闭！
    pause
    exit /b 1
)

:: 检查 E 盘目标是否存在
if not exist "E:\AppData\Claude\vm_bundles" (
    echo [ERROR] E:\AppData\Claude 不完整，请勿运行此脚本！
    pause
    exit /b 1
)

echo [1/3] 删除 C 盘残留的 Claude 目录...
rmdir /S /Q "%APPDATA%\Claude"
if exist "%APPDATA%\Claude" (
    echo [WARN] 部分文件未能删除，尝试强制清理...
    timeout /t 2 /nobreak >nul
    rmdir /S /Q "%APPDATA%\Claude" 2>nul
)

if exist "%APPDATA%\Claude" (
    echo [ERROR] 无法删除 C 盘 Claude 目录，可能仍有进程占用。
    echo         请确认所有 Claude 相关进程已关闭后重试。
    pause
    exit /b 1
)

echo [2/3] 创建符号链接 C 盘 -^> E 盘...
mklink /D "%APPDATA%\Claude" "E:\AppData\Claude"
if %errorlevel% neq 0 (
    echo [ERROR] 创建符号链接失败！
    echo         请确认已以管理员身份运行。
    pause
    exit /b 1
)

echo [3/3] 验证...
dir "%APPDATA%\Claude\vm_bundles" >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo ============================================
    echo  迁移完成！
    echo  C:\Users\Administrator\AppData\Roaming\Claude
    echo    --^> E:\AppData\Claude （符号链接）
    echo  C 盘释放约 12 GB 空间
    echo  现在可以正常启动 Claude 了
    echo ============================================
) else (
    echo [ERROR] 验证失败，符号链接可能有问题。
)

pause
