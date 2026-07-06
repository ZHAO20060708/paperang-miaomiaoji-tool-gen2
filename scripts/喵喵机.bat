@echo off
cd /d "%~dp0.."

echo ========================================
echo   喵喵机2 Paperang 打印工具
echo ========================================
echo.
echo   [1] 交互模式（手动输入打印内容）
echo   [2] 命令行模式（查看帮助）
echo   [3] 打印自检页
echo   [4] 安装/更新依赖
echo.
set /p choice="Select (1/2/3/4): "

if "%choice%"=="1" (
    uv run python -m paperang interactive
) else if "%choice%"=="2" (
    uv run python -m paperang --help
) else if "%choice%"=="3" (
    uv run python -m paperang selftest
) else if "%choice%"=="4" (
    uv sync
) else (
    echo 无效选择
)

pause
