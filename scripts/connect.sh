#!/usr/bin/env bash
# 快捷连接/测试喵喵机脚本

MAC="FC:58:FA:C1:7C:51"
DEV="/dev/rfcomm0"

# 检查 rfcomm 绑定状态
if ! rfcomm show 0 >/dev/null 2>&1; then
    echo "提示: /dev/rfcomm0 未绑定，正在拉起权限进行绑定..."
    pkexec rfcomm bind 0 "$MAC" 1
    if [ $? -ne 0 ]; then
        echo "错误: 绑定失败，请检查密码或蓝牙是否开启。"
        exit 1
    fi
    echo "成功绑定 $MAC 到 $DEV"
else
    echo "信息: $DEV 已经绑定到 $MAC"
fi

# 测试打印机响应
echo "正在测试打印机连接状态..."
cd /home/eric/playground/paperang-miaomiaoji-tool-gen2 || exit 1
uv run python -m paperang status

if [ $? -eq 0 ]; then
    echo "----------------------------------------"
    echo "连接测试成功！打印机就绪。"
else
    echo "----------------------------------------"
    echo "警告: 无法与打印机通信，请确保打印机已开机且在蓝牙范围内。"
fi
