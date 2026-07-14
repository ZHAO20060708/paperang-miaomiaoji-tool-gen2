#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Script to fetch and print fun content on the Paperang P2 printer."""

import sys
import os
import subprocess
import argparse
import urllib.request
import json
from datetime import datetime

# Add the project root to python path to import paperang modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paperang.config import setup_config
from paperang.bt import BtManager
from paperang.text import TextConverter


def get_fastfetch():
    """Run fastfetch and return its plain text output."""
    try:
        # Using --pipe to disable ANSI colors and get raw text
        res = subprocess.run(["fastfetch", "--pipe"], capture_output=True, text=True, check=True)
        return res.stdout
    except Exception as e:
        return f"获取 fastfetch 失败: {e}"


def get_weather():
    """Fetch ASCII weather report from wttr.in."""
    try:
        # Fetching wttr.in with ?0 (current weather only) and disabling colors/ansi
        req = urllib.request.Request(
            "http://wttr.in?0&T", 
            headers={"User-Agent": "curl/7.79.1"} # wttr.in returns ascii art for curl user agent
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            html = response.read().decode('utf-8')
            # Remove ANSI escape codes just in case, though wttr.in?T should be plain
            return html
    except Exception as e:
        return f"获取天气失败: {e}"


def get_calendar():
    """Run cal and return the current month calendar."""
    try:
        res = subprocess.run(["cal"], capture_output=True, text=True, check=True)
        return res.stdout
    except Exception as e:
        return f"获取日历失败: {e}"


def get_joke():
    """Fetch a safe programming joke from JokeAPI."""
    url = "https://v2.jokeapi.dev/joke/Programming?type=single&safe-mode"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "python-urllib"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            if not data.get("error"):
                return data.get("joke")
            return "未能获取笑话数据，请检查网络连接。"
    except Exception as e:
        return f"获取笑话失败: {e}"


def print_content(mmj, title, text, font_size=20, feed=0):
    """Format and print content with a header."""
    print(f"正在打印: {title} (字号 {font_size})...")
    
    # Format the print block
    block = []
    if title:
        block.append("=" * 30)
        block.append(f" {title} ".center(30, "*"))
        block.append("=" * 30)
        block.append("")
    block.append(text)
    block.append("")
    
    full_text = "\n".join(block)
    img = TextConverter.text2bmp(full_text, font_size=font_size)
    mmj.sendImageToBt(img)
    if feed > 0:
        mmj.sendFeedLineToBt(feed)


def main():
    parser = argparse.ArgumentParser(description="喵喵机趣味命令输出打印工具")
    parser.add_argument("type", choices=["fastfetch", "weather", "cal", "joke", "all"],
                        help="要打印的内容类型")
    parser.add_argument("-f", "--feed", type=int, default=250, help="打印完走纸长度 (默认250)")
    parser.add_argument("--font-size", type=int, help="覆盖默认字号")
    args = parser.parse_args()

    # Load printer config
    cfg = setup_config()
    mmj = BtManager(cfg)
    if not mmj.connected:
        print("Error: 无法连接到打印机，请检查配置或打印机是否开机。", file=sys.stderr)
        sys.exit(1)

    mmj.registerCrcKeyToBt()
    mmj.sendDensityToBt(100)
    mmj.sendPowerOffTimeToBt(0)

    try:
        if args.type == "fastfetch":
            font_size = args.font_size or 15
            text = get_fastfetch()
            print_content(mmj, "System Specs (Fastfetch)", text, font_size=font_size, feed=args.feed)
            
        elif args.type == "weather":
            font_size = args.font_size or 22
            text = get_weather()
            print_content(mmj, "Weather Report", text, font_size=font_size, feed=args.feed)
            
        elif args.type == "cal":
            font_size = args.font_size or 28
            text = get_calendar()
            print_content(mmj, "Calendar", text, font_size=font_size, feed=args.feed)
            
        elif args.type == "joke":
            font_size = args.font_size or 26
            text = get_joke()
            print_content(mmj, "Programming Joke", text, font_size=font_size, feed=args.feed)
            
        elif args.type == "all":
            # Print fastfetch (no feed)
            ff_text = get_fastfetch()
            print_content(mmj, "System Specs (Fastfetch)", ff_text, font_size=15, feed=0)
            
            # Print weather (no feed)
            wt_text = get_weather()
            print_content(mmj, "Weather Report", wt_text, font_size=22, feed=0)
            
            # Print calendar (no feed)
            cal_text = get_calendar()
            print_content(mmj, "Calendar", cal_text, font_size=28, feed=0)
            
            # Print joke (with feed)
            jk_text = get_joke()
            print_content(mmj, "Programming Joke", jk_text, font_size=26, feed=args.feed)
            
        print("打印指令发送成功！")
    finally:
        mmj.disconnect()


if __name__ == "__main__":
    main()
