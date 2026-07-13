"""Bluetooth / serial communication manager for Paperang 2 printer."""

import struct
import zlib
import logging
import serial

from paperang.const import BtCommandByte


class BtManager:
    """Manages Bluetooth SPP serial communication with the Paperang 2 printer."""

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
        except Exception:
            pass
        logging.info("Disconnected.")

    def sendMsgAllPackage(self, msg):
        sent_len = 0
        for i in range(0, len(msg), self.max_send_msg_length):
            sent_len += self.sock.write(msg[i:i + self.max_send_msg_length])

    def crc32(self, content):
        return zlib.crc32(content, self.crcKey if self.crckeyset else self.standardKey)

    def packPerBytes(self, bytes_data, control_command, i):
        result = struct.pack('<BBB', 2, control_command, i)
        result += struct.pack('<H', len(bytes_data))
        result += bytes_data
        result += struct.pack('<I', self.crc32(bytes_data))
        result += struct.pack('<B', 3)
        return result

    def addBytesToList(self, bytes_data):
        length = self.max_send_msg_length
        result = [bytes_data[i:i + length] for i in range(0, len(bytes_data), length)]
        return result

    def sendToBt(self, allbytes, control_command, need_reply=True):
        bytes_list = self.addBytesToList(allbytes)
        for i, bytes_data in enumerate(bytes_list):
            tmp = self.packPerBytes(bytes_data, control_command, i)
            self.sendMsgAllPackage(tmp)
        if need_reply:
            return self.recv()

    def recv(self):
        data = self.sock.read(self.max_recv_msg_length)
        if not data:
            return None
        return self.parseResponse(data)

    def parseResponse(self, data):
        base = 0
        results = []
        while base < len(data) and data[base] == 0x02:
            if base + 5 > len(data):
                break
            _, command, _, payload_length = struct.unpack('<BBBH', data[base:base + 5])
            payload = data[base + 5: base + 5 + payload_length]
            base += 10 + payload_length
            results.append({"command": command, "payload": payload})
        return results if results else data

    # ── high-level commands ──────────────────────────────────────────

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
        line_bytes = 72  # 576 pixels / 8 = 72 bytes per line
        for i in range(0, len(binary_img), line_bytes):
            line = binary_img[i:i + line_bytes]
            self.sendToBt(line, BtCommandByte.PRT_PRINT_DATA, need_reply=False)

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
        return self.sendToBt(msg, BtCommandByte.PRT_GET_BAT_STATUS)

    def queryDensity(self):
        msg = struct.pack('<B', 1)
        return self.sendToBt(msg, BtCommandByte.PRT_GET_HEAT_DENSITY)

    def sendFeedToHeadLineToBt(self, length):
        msg = struct.pack('<H', length)
        self.sendToBt(msg, BtCommandByte.PRT_FEED_TO_HEAD_LINE)

    def queryPowerOffTime(self):
        msg = struct.pack('<B', 1)
        return self.sendToBt(msg, BtCommandByte.PRT_GET_POWER_DOWN_TIME)

    def querySNFromBt(self):
        msg = struct.pack('<B', 1)
        return self.sendToBt(msg, BtCommandByte.PRT_GET_SN)

    def queryHardwareInfo(self):
        msg = struct.pack('<B', 1)
        return self.sendToBt(msg, BtCommandByte.PRT_GET_HW_INFO)
