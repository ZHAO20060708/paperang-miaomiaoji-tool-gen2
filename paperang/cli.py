#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Paperang 2 (喵喵机2) command-line print tool.

Usage:
    python -m paperang text "hello"
    python -m paperang image photo.jpg
    python -m paperang qrcode "https://example.com"
    python -m paperang interactive
"""

import argparse
import os
import sys
import logging

from paperang.config import setup_config, load_config, list_serial_ports, save_config
from paperang.bt import BtManager
from paperang.image import ImageConverter
from paperang.text import TextConverter


def init_printer(args):
    """Connect to printer, register CRC key, set defaults."""
    cfg = setup_config()
    if args.port:
        cfg["serial_port"] = args.port
    mmj = BtManager(cfg)
    if not mmj.connected:
        print("打印机连接失败，请检查串口配置与设备连接。", file=sys.stderr)
        sys.exit(1)
    mmj.registerCrcKeyToBt()
    density = args.density if hasattr(args, 'density') and args.density is not None else 100
    mmj.sendDensityToBt(density)
    mmj.sendPowerOffTimeToBt(0)
    return mmj


def _decode_escapes(s):
    return s.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r').replace('\\\\', '\\')


# ── subcommand handlers ──────────────────────────────────────────────

def cmd_text(args):
    mmj = init_printer(args)
    text = args.text
    if text == '-':
        # Read all text from standard input
        text = sys.stdin.read()
    text = _decode_escapes(text)
    img = TextConverter.text2bmp(text, font_size=args.font_size, font_path=args.font)
    mmj.sendImageToBt(img)
    if args.feed:
        mmj.sendFeedLineToBt(args.feed)
    mmj.disconnect()


def cmd_image(args):
    mmj = init_printer(args)
    if not os.path.isfile(args.path):
        print(f"文件不存在: {args.path}", file=sys.stderr)
        sys.exit(1)
    img_data = ImageConverter.process_image_for_printing_with_mode(
        args.path, args.mode, no_rotate=args.no_rotate)
    mmj.sendImageToBt(img_data)
    if args.feed:
        mmj.sendFeedLineToBt(args.feed)
    mmj.disconnect()


def cmd_qrcode(args):
    mmj = init_printer(args)
    img_data = ImageConverter.generate_qr_code(args.text)
    mmj.sendImageToBt(img_data)
    if args.feed:
        mmj.sendFeedLineToBt(args.feed)
    mmj.disconnect()


def cmd_selftest(args):
    mmj = init_printer(args)
    mmj.sendSelfTestToBt()
    mmj.disconnect()


def cmd_feed(args):
    mmj = init_printer(args)
    mmj.sendFeedLineToBt(args.length)
    mmj.disconnect()


def _print_reply(label, data):
    if data is None:
        print(f"  {label}: (无响应)")
    elif isinstance(data, list):
        for item in data:
            payload = item["payload"]
            print(f"  {label}: {payload.hex() if payload else '(空)'}")
    elif isinstance(data, (bytes, bytearray)):
        print(f"  {label}: {data.hex()}")
    else:
        print(f"  {label}: {data}")


def cmd_status(args):
    mmj = init_printer(args)
    if args.battery:
        _print_reply("电池", mmj.queryBatteryStatus())
    elif args.sn:
        _print_reply("序列号", mmj.querySNFromBt())
    elif args.hardware:
        _print_reply("硬件信息", mmj.queryHardwareInfo())
    else:
        _print_reply("电池", mmj.queryBatteryStatus())
        _print_reply("序列号", mmj.querySNFromBt())
        _print_reply("硬件信息", mmj.queryHardwareInfo())
    mmj.disconnect()


def cmd_config(args):
    cfg = load_config()
    if args.set_port:
        cfg["serial_port"] = args.set_port
        save_config(cfg)
        print(f"已设置串口: {args.set_port}")
        return
    if args.list:
        ports = list_serial_ports()
        print("当前可用串口:")
        for device, desc in ports:
            marker = " *" if device == cfg.get("serial_port") else ""
            print(f"  {device} - {desc}{marker}")
        return
    print(f"当前配置: {cfg}")


def cmd_interactive(args):
    """Launch the interactive terminal UI (for human users)."""
    from paperang.interactive import PrinterCLI

    logging.getLogger().setLevel(logging.INFO)
    cfg = setup_config()
    mmj = BtManager(cfg)
    cli = PrinterCLI(mmj)
    cli.run()


# ── main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="paperang",
        description="喵喵机2 Paperang 命令行打印工具"
    )
    parser.add_argument("-p", "--port", help="指定串口（覆盖配置文件）")
    parser.add_argument("-d", "--density", type=int, choices=range(1, 101), metavar="1-100",
                        help="打印浓度 (1-100，默认100)")
    subparsers = parser.add_subparsers(dest="command")

    # text
    p_text = subparsers.add_parser("text", help="打印文字")
    p_text.add_argument("text", help="要打印的文字内容")
    p_text.add_argument("--font-size", type=int, default=24, help="字体大小 (默认24)")
    p_text.add_argument("--font", help="自定义字体：文件路径(.ttf/.otf)或系统字体名称")
    p_text.add_argument("--feed", type=int, default=0, help="打印后走纸长度，连续打印时设为0，最后统一走纸")
    p_text.set_defaults(func=cmd_text)

    # image
    p_img = subparsers.add_parser("image", help="打印图片")
    p_img.add_argument("path", help="图片路径")
    p_img.add_argument("--mode", choices=["floyd", "adaptive", "auto", "f", "a"], default="floyd",
                       help="图像处理模式: floyd/adaptive/auto (默认floyd)")
    p_img.add_argument("--no-rotate", action="store_true", help="禁用自动旋转")
    p_img.add_argument("--feed", type=int, default=0, help="打印后走纸长度，连续打印时设为0，最后统一走纸")
    p_img.set_defaults(func=cmd_image)

    # qrcode
    p_qr = subparsers.add_parser("qrcode", help="打印二维码")
    p_qr.add_argument("text", help="二维码内容")
    p_qr.add_argument("--feed", type=int, default=0, help="打印后走纸长度，连续打印时设为0，最后统一走纸")
    p_qr.set_defaults(func=cmd_qrcode)

    # selftest
    p_test = subparsers.add_parser("selftest", help="打印自检页")
    p_test.set_defaults(func=cmd_selftest)

    # feed
    p_feed = subparsers.add_parser("feed", help="走纸")
    p_feed.add_argument("length", type=int, help="走纸长度")
    p_feed.set_defaults(func=cmd_feed)

    # status
    p_status = subparsers.add_parser("status", help="查询打印机状态")
    p_status.add_argument("--battery", action="store_true", help="查询电池状态")
    p_status.add_argument("--sn", action="store_true", help="查询序列号")
    p_status.add_argument("--hardware", action="store_true", help="查询硬件信息")
    p_status.set_defaults(func=cmd_status)

    # config
    p_cfg = subparsers.add_parser("config", help="查看或修改配置")
    p_cfg.add_argument("--list", action="store_true", help="列出可用串口")
    p_cfg.add_argument("--set-port", help="直接设置串口，例如 COM10")
    p_cfg.set_defaults(func=cmd_config)

    # interactive
    p_inter = subparsers.add_parser("interactive", help="启动交互式终端模式（用户直接使用）")
    p_inter.set_defaults(func=cmd_interactive)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    logging.getLogger().setLevel(logging.INFO)
    args.func(args)


if __name__ == "__main__":
    main()
