from image_process import TextConverter, ImageConverter
import struct, zlib, logging
import os
from const import BtCommandByte
import serial
import time
import qrcode

class BtManager:
    max_send_msg_length = 1008 
    max_recv_msg_length = 1024
    standardKey = 0x00000000

    def __init__(self, address=None):
        self.crckeyset = False
        self.connected = True if self.connect() else False

    def connect(self):
        self.sock = serial.Serial('COM10', 115200, timeout=1)
        return True

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
        # Here we assume that there is only one received packet.
        # raw_msg = self.sock.recv(self.max_recv_msg_length)
        # parsed = self.resultParser(raw_msg)
        # logging.info("Recv: " + raw_msg.encode('hex'))
        # logging.info("Received %d packets: " % len(parsed) + "".join([str(p) for p in parsed]))
        # return raw_msg, parsed
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
        # My guess:
        # paperType=0: normal paper
        # paperType=1: official paper
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

def printImg(img_bytes):
    for i in range(0, len(img_bytes)*8):
        print("*" if img_bytes[i//8]>>(7-(i%8))&0x01 == 1 else ".", end="")
        if (i+1)%384==0:
            print("|")
            
if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    # 打印使用提示
    help_text = """欢迎使用Paperang2终端打印工具@2025
反馈邮箱：createskyblue@outlook.com
项目地址：https://github.com/createskyblue/miaomiaoji-tool-gen2
感谢：https://github.com/ihciah/miaomiaoji-tool
字体来自：https://github.com/subframe7536/maple-font
项目为MIT协议

支持的指令:
/selftest     - 打印自检页
/fontsize <int> - 设置字体大小 (默认24)
/qrcode <string> - 生成并打印二维码
/help         - 显示此帮助信息

请输入图片路径或文字内容，支持jpg、png、bmp、gif、jpeg格式图片
"""
    print(help_text)

    mmj = BtManager()
    if mmj.connected:
        mmj.registerCrcKeyToBt()
        mmj.sendDensityToBt(100)
        mmj.sendPowerOffTimeToBt(0)
        font_size = 24
        text="miaomiaoji-tool\n[" + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "]\nPAPERANG终端已连接\n等待用户输入\n>>>\n\n\n\n\n\n"
        text=""
        while(1):
            if (text==""):
                # 换行
                mmj.sendFeedLineToBt(25)
            elif (text=="/selftest"):
                mmj.sendSelfTestToBt()
                text=""
            elif text.startswith("/fontsize "):
                try:
                    new_font_size = int(text.split(" ")[1])
                    if 8 <= new_font_size <= 72:
                        font_size = new_font_size
                        print(f"字体大小已设置为: {font_size}")
                    else:
                        print("字体大小应在8-72之间")
                except ValueError:
                    print("无效的字体大小，请输入数字")
                except IndexError:
                    print("请提供字体大小，例如: /fontsize 24")
            elif text.startswith("/qrcode "):
                try:
                    qr_string = text[8:]  # 提取二维码内容
                    if qr_string:
                        # 生成二维码
                        qr = qrcode.QRCode(
                            version=1,
                            error_correction=qrcode.constants.ERROR_CORRECT_L,
                            box_size=4,
                            border=4,
                        )
                        qr.add_data(qr_string)
                        qr.make(fit=True)
                        qr_img = qr.make_image(fill_color="black", back_color="white")
                        
                        # 转换为二值图像并打印（使用im2bmp方法）
                        img_data = ImageConverter.im2bmp(qr_img)
                        mmj.sendImageToBt(img_data)
                    else:
                        print("请提供二维码内容，例如: /qrcode Hello World")
                except Exception as e:
                    print(f"二维码生成失败: {e}")
                text=""
            elif text == "/help":
                print(help_text)
                img = TextConverter.text2bmp(help_text, font_size=font_size)
                mmj.sendImageToBt(img)
            elif os.path.isfile(text) and any(text.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.bmp']):
                # 处理图片打印
                try:
                    img_data = ImageConverter.process_image_for_printing(text)
                    mmj.sendImageToBt(img_data)
                except Exception as e:
                    print(f"图片打印失败: {e}")
                text=""
            else:
                img = TextConverter.text2bmp(text, font_size=font_size)
                mmj.sendImageToBt(img)
            
            #捕获用户输入
            text = input("喵喵机2 >")
    else:
        logging.error("Oops! Cannot establish connection with Paperang devices.")