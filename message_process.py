from image_process import TextConverter, ImageConverter
import struct, zlib, logging
import os
import sys
from const import BtCommandByte
import serial
import time

# 添加全局变量来存储图像处理模式
image_process_mode = "floyd"  # 默认使用扩散模式


class BtManager:
    max_send_msg_length = 1008
    max_recv_msg_length = 1024
    standardKey = 0x00000000

    def __init__(self, cfg):
        self.crckeyset = False
        self.cfg = cfg
        self.connected = True if self.connect() else False

    def connect(self):
        try:
            self.sock = serial.Serial(
                self.cfg["serial_port"],
                self.cfg.get("baudrate", 115200),
                timeout=self.cfg.get("timeout", 1)
            )
            return True
        except Exception as e:
            logging.error(f"串口连接失败: {e}")
            return False

    def disconnect(self):
        try:
            self.sock.close()
        except:
            pass
        logging.info("Disconnected.")

    def sendMsgAllPackage(self, msg):
        sent_len = 0
        for i in range(0, len(msg), self.max_send_msg_length):
            sent_len += self.sock.write(msg[i:i+self.max_send_msg_length])

    def crc32(self, content):
        return zlib.crc32(content, self.crcKey if self.crckeyset else self.standardKey)

    def packPerBytes(self, bytes, control_command, i):
        result = struct.pack('<BBB', 2, control_command, i)
        result += struct.pack('<H', len(bytes))
        result += bytes
        result += struct.pack('<I', self.crc32(bytes))
        result += struct.pack('<B', 3)
        return result

    def addBytesToList(self, bytes):
        length = self.max_send_msg_length
        result = [bytes[i:i+length] for i in range(0, len(bytes), length)]
        return result

    def sendToBt(self, allbytes, control_command, need_reply=True):
        bytes_list = self.addBytesToList(allbytes)
        for i, bytes in enumerate(bytes_list):
            tmp = self.packPerBytes(bytes, control_command, i)
            self.sendMsgAllPackage(tmp)
        if need_reply:
            return self.recv()

    def recv(self):
        pass

    def resultParser(self, data):
        base = 0
        res = []
        while base < len(data) and data[base] == '\x02':
            class Info(object):
                def __str__(self):
                    return "\nControl command: %s(%s)\nPayload length: %d\nPayload(hex): %s" % (
                        self.command, BtCommandByte.findCommand(self.command)
                        , self.payload_length, self.payload.encode('hex')
                    )
            info = Info()
            _, info.command, _, info.payload_length = struct.unpack('<BBBH', data[base:base+5])
            info.payload = data[base + 5: base + 5 + info.payload_length]
            info.crc32 = data[base + 5 + info.payload_length: base + 9 + info.payload_length]
            base += 10 + info.payload_length
            res.append(info)
        return res

    def registerCrcKeyToBt(self):
        self.sendMsgAllPackage(bytes.fromhex("0218000400219576351cdf442103"))

    def sendPaperTypeToBt(self, paperType=0):
        msg = struct.pack('<B', paperType)
        self.sendToBt(msg, BtCommandByte.PRT_SET_PAPER_TYPE)

    def sendPowerOffTimeToBt(self, poweroff_time=0):
        msg = struct.pack('<H', poweroff_time)
        self.sendToBt(msg, BtCommandByte.PRT_SET_POWER_DOWN_TIME)

    def sendImageToBt(self, binary_img):
        self.sendPaperTypeToBt()
        msg = binary_img
        self.sendToBt(msg, BtCommandByte.PRT_PRINT_DATA, need_reply=False)

    def sendSelfTestToBt(self):
        msg = struct.pack('<B', 0)
        self.sendToBt(msg, BtCommandByte.PRT_PRINT_TEST_PAGE)

    def sendDensityToBt(self, density):
        msg = struct.pack('<B', density)
        self.sendToBt(msg, BtCommandByte.PRT_SET_HEAT_DENSITY)

    def sendFeedLineToBt(self, length):
        msg = struct.pack('<H', length)
        self.sendToBt(msg, BtCommandByte.PRT_FEED_LINE)

    def queryBatteryStatus(self):
        msg = struct.pack('<B', 1)
        self.sendToBt(msg, BtCommandByte.PRT_GET_BAT_STATUS)

    def queryDensity(self):
        msg = struct.pack('<B', 1)
        self.sendToBt(msg, BtCommandByte.PRT_GET_HEAT_DENSITY)

    def sendFeedToHeadLineToBt(self, length):
        msg = struct.pack('<H', length)
        self.sendToBt(msg, BtCommandByte.PRT_FEED_TO_HEAD_LINE)

    def queryPowerOffTime(self):
        msg = struct.pack('<B', 1)
        self.sendToBt(msg, BtCommandByte.PRT_GET_POWER_DOWN_TIME)

    def querySNFromBt(self):
        msg = struct.pack('<B', 1)
        self.sendToBt(msg, BtCommandByte.PRT_GET_SN)

    def queryHardwareInfo(self):
        msg = struct.pack('<B', 1)
        self.sendToBt(msg, BtCommandByte.PRT_GET_HW_INFO)


class PrinterCLI:
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
项目地址：https://github.com/createskyblue/miaomiaoji-tool-gen2
感谢：https://github.com/ihciah/miaomiaoji-tool
字体来自：https://github.com/subframe7536/maple-font
项目为MIT协议

支持的指令:
/selftest        - 打印自检页
/fontsize <int>  - 设置字体大小 (默认24)
/qrcode <string> - 生成并打印二维码
/imgmode <mode>  - 设置图像处理模式  floyd(缩写f) 或 adaptive(缩写a)
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
        elif os.path.isfile(text) and any(text.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']):
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
    for i in range(0, len(img_bytes)*8):
        print("*" if img_bytes[i//8]>>(7-(i%8))&0x01 == 1 else ".", end="")
        if (i+1)%384==0:
            print("|")


if __name__ == "__main__":
    from config import setup_config
    logging.getLogger().setLevel(logging.INFO)
    cfg = setup_config()
    mmj = BtManager(cfg)
    cli = PrinterCLI(mmj)
    cli.run()
