@echo off
chcp 65001 >nul
echo ========================================
echo   喵喵机2 Paperang 打印工具
echo ========================================
echo.
echo   [1] 交互模式（手动输入打印内容）
echo   [2] 命令行模式（查看帮助）
echo   [3] 打印自检页
echo.
set /p choice="请选择 (1/2/3): "

if "%choice%"=="1" (
    python -m paperang interactive
) else if "%choice%"=="2" (
    python -m paperang --help
) else if "%choice%"=="3" (
    python -m paperang selftest
) else (
    echo 无效选择
)

pause
