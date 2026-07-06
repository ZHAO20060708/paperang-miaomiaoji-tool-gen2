#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interactive terminal UI for the Paperang 2 printer (for direct human use).

Launch via:
    python paperang/interactive.py
    python -m paperang interactive
"""

import os
import logging

from paperang.image import ImageConverter
from paperang.text import TextConverter

# Global image processing mode
image_process_mode = "floyd"


class PrinterCLI:
    """Interactive command-line interface for the Paperang 2 printer."""

    def __init__(self, mmj):
        self.mmj = mmj
        self.font_size = 24

    def run(self):
        help_text = self._help_text()
        print(help_text)

        if self.mmj.connected:
            self.mmj.registerCrcKeyToBt()
            self.mmj.sendDensityToBt(100)
            self.mmj.sendPowerOffTimeToBt(0)
            text = ""
            while True:
                self._process_text(text)
                try:
                    text = input("喵喵机2 > ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n退出。")
                    break
        else:
            logging.error("Oops! Cannot establish connection with Paperang devices.")

    def _help_text(self):
        return """欢迎使用Paperang2终端打印工具@2025
反馈邮箱：createskyblue@outlook.com
项目地址：https://github.com/createskyblue/paperang-miaomiaoji-tool-gen2
感谢：https://github.com/ihciah/miaomiaoji-tool
字体来自：https://github.com/subframe7536/maple-font
项目为MIT协议

支持的指令:
/selftest        - 打印自检页
/fontsize <int>  - 设置字体大小 (默认24)
/qrcode <string> - 生成并打印二维码
/imgmode <mode>  - 设置图像处理模式 floyd(缩写f) 或 adaptive(缩写a)
/help            - 显示此帮助信息

请输入图片路径或文字内容，支持jpg、png、bmp、gif、jpeg格式图片
"""

    def _process_text(self, text):
        global image_process_mode
        if text == "":
            self.mmj.sendFeedLineToBt(25)
        elif text == "/selftest":
            self.mmj.sendSelfTestToBt()
        elif text.startswith("/fontsize "):
            self._set_fontsize(text)
        elif text.startswith("/imgmode "):
            image_process_mode = self._set_imgmode(text) or image_process_mode
        elif text.startswith("/qrcode "):
            self._print_qrcode(text)
        elif text == "/help":
            print(self._help_text())
            img = TextConverter.text2bmp(self._help_text(), font_size=self.font_size)
            self.mmj.sendImageToBt(img)
        elif os.path.isfile(text) and any(
            text.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
        ):
            self._print_image(text)
        elif text:
            img = TextConverter.text2bmp(text, font_size=self.font_size)
            self.mmj.sendImageToBt(img)

    def _set_fontsize(self, text):
        try:
            new_font_size = int(text.split(" ")[1])
            if 8 <= new_font_size <= 72:
                self.font_size = new_font_size
                print(f"字体大小已设置为: {self.font_size}")
            else:
                print("字体大小应在8-72之间")
        except (ValueError, IndexError):
            print("无效的字体大小，例如: /fontsize 24")

    def _set_imgmode(self, text):
        try:
            mode = text.split(" ")[1].lower()
            if mode in ["floyd", "adaptive", "f", "a"]:
                print(f"图像处理模式已设置为: {mode}")
                ImageConverter.current_mode = mode
                return mode
            else:
                print("无效的图像处理模式，请使用 floyd(f) 或 adaptive(a)")
        except IndexError:
            print("请提供图像处理模式，例如: /imgmode f")
        return None

    def _print_qrcode(self, text):
        try:
            qr_string = text[8:].strip()
            if qr_string:
                img_data = ImageConverter.generate_qr_code(qr_string)
                self.mmj.sendImageToBt(img_data)
            else:
                print("请提供二维码内容，例如: /qrcode Hello World")
        except Exception as e:
            print(f"二维码生成失败: {e}")

    def _print_image(self, image_path):
        try:
            img_data = ImageConverter.process_image_for_printing_with_mode(image_path, image_process_mode)
            self.mmj.sendImageToBt(img_data)
        except Exception as e:
            print(f"图片打印失败: {e}")


def printImg(img_bytes):
    """Debug helper: print image bytes as ASCII art."""
    for i in range(0, len(img_bytes) * 8):
        print("*" if img_bytes[i // 8] >> (7 - (i % 8)) & 0x01 == 1 else ".", end="")
        if (i + 1) % 384 == 0:
            print("|")


if __name__ == "__main__":
    from paperang.config import setup_config
    from paperang.bt import BtManager

    logging.getLogger().setLevel(logging.INFO)
    cfg = setup_config()
    mmj = BtManager(cfg)
    cli = PrinterCLI(mmj)
    cli.run()
