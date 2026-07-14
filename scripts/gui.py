#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PySide6 GUI application for Paperang P2 printer."""

import sys
import os
import subprocess
import json
import urllib.request
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTextEdit, QPushButton, QLabel, QSpinBox, QComboBox,
    QFileDialog, QProgressBar, QMessageBox, QGroupBox, QLineEdit, QSlider
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QPixmap, QImage

# Add the project root to python path to import paperang modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paperang.config import setup_config, save_config, list_serial_ports
from paperang.bt import BtManager
from paperang.text import TextConverter
from paperang.image import ImageConverter

# --- Styling (QSS) ---
MODERN_STYLE = """
QMainWindow {
    background-color: #1e1e24;
}
QWidget {
    color: #e2e2e7;
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 14px;
}
QGroupBox {
    border: 2px solid #2e2e38;
    border-radius: 8px;
    margin-top: 12px;
    font-weight: bold;
    color: #00adb5;
    padding-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 3px;
}
QTabWidget::pane {
    border: 1px solid #2e2e38;
    background: #1e1e24;
    border-radius: 6px;
}
QTabBar::tab {
    background: #25252d;
    border: 1px solid #2e2e38;
    padding: 8px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected, QTabBar::tab:hover {
    background: #2e2e38;
    color: #00adb5;
    border-bottom-color: #1e1e24;
}
QTextEdit, QLineEdit {
    background-color: #25252d;
    border: 1px solid #3e3e4a;
    border-radius: 6px;
    padding: 6px;
    color: #ffffff;
}
QTextEdit:focus, QLineEdit:focus {
    border: 1px solid #00adb5;
}
QPushButton {
    background-color: #00adb5;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #008c9e;
}
QPushButton:pressed {
    background-color: #005f73;
}
QPushButton:disabled {
    background-color: #3e3e4a;
    color: #8e8e93;
}
QComboBox, QSpinBox {
    background-color: #25252d;
    border: 1px solid #3e3e4a;
    border-radius: 6px;
    padding: 5px;
    color: #ffffff;
}
QComboBox::drop-down {
    border: none;
}
QLabel {
    color: #e2e2e7;
}
"""

# --- Background Worker for Async Printer Actions ---
class PrinterWorker(QThread):
    finished = Signal(bool, str)  # success, message

    def __init__(self, action_type, **kwargs):
        super().__init__()
        self.action_type = action_type
        self.kwargs = kwargs

    def run(self):
        try:
            cfg = setup_config()
            mmj = BtManager(cfg)
            if not mmj.connected:
                self.finished.emit(False, "无法连接到打印机，请检查串口或确认打印机已开机。")
                return

            mmj.registerCrcKeyToBt()
            mmj.sendDensityToBt(100)
            mmj.sendPowerOffTimeToBt(0)

            if self.action_type == "text":
                text = self.kwargs.get("text", "")
                font_size = self.kwargs.get("font_size", 24)
                img = TextConverter.text2bmp(text, font_size=font_size)
                mmj.sendImageToBt(img)
                mmj.sendFeedLineToBt(250)

            elif self.action_type == "image":
                path = self.kwargs.get("path", "")
                mode = self.kwargs.get("mode", "floyd")
                img_data = ImageConverter.process_image_for_printing_with_mode(path, mode)
                mmj.sendImageToBt(img_data)
                mmj.sendFeedLineToBt(250)

            elif self.action_type == "qrcode":
                content = self.kwargs.get("content", "")
                img_data = ImageConverter.generate_qr_code(content)
                mmj.sendImageToBt(img_data)
                mmj.sendFeedLineToBt(250)

            elif self.action_type == "feed":
                length = self.kwargs.get("length", 100)
                mmj.sendFeedLineToBt(length)

            elif self.action_type == "selftest":
                mmj.sendSelfTestToBt()

            elif self.action_type == "status":
                bat = mmj.queryBatteryStatus()
                sn = mmj.querySNFromBt()
                hw = mmj.queryHardwareInfo()
                
                # Format response nicely
                info = []
                if bat and len(bat) > 0:
                    # Parse battery if possible or show raw
                    info.append(f"电池电量: 已连接 (有响应)")
                else:
                    info.append("电池电量: 无响应")
                if sn and len(sn) > 0:
                    try:
                        # Extract serial number hex to text
                        payload = sn[0]["payload"]
                        sn_str = payload.decode('utf-8', errors='ignore').strip()
                        info.append(f"序列号: {sn_str}")
                    except Exception:
                        info.append(f"序列号: {sn}")
                else:
                    info.append("序列号: 无响应")
                
                self.finished.emit(True, "\n".join(info))
                mmj.disconnect()
                return

            mmj.disconnect()
            self.finished.emit(True, "打印指令发送成功！")
        except Exception as e:
            err_msg = str(e)
            if "Errno 5" in err_msg or "input/output error" in err_msg.lower():
                self.finished.emit(False, "连接失败：输入/输出错误 (Errno 5)。\n\n这通常是因为：\n1. 喵喵机自动关机了（长按电源键开机，绿灯亮起即可）\n2. 打印机超出了蓝牙接收范围\n3. 蓝牙模块被挂起。请确认打印机已开机，然后再次尝试。")
            else:
                self.finished.emit(False, f"执行出错: {err_msg}")


# --- MainWindow UI ---
class PaperangGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🖨️ 喵喵机 P2 桌面控制台")
        self.resize(700, 500)
        self.setStyleSheet(MODERN_STYLE)

        # Central Widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Header Status Panel
        status_layout = QHBoxLayout()
        self.status_label = QLabel("🔋 状态: 准备就绪 (未连接测试)")
        self.status_label.setStyleSheet("font-weight: bold; color: #00adb5;")
        self.test_status_btn = QPushButton("测试连接")
        self.test_status_btn.setStyleSheet("background-color: #2e2e38; color: #00adb5; border: 1px solid #00adb5;")
        self.test_status_btn.clicked.connect(self.test_connection)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.test_status_btn)
        main_layout.addLayout(status_layout)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.init_text_tab()
        self.init_image_tab()
        self.init_fun_tab()
        self.init_config_tab()

        # Loading / Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminate
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #00adb5; }")
        main_layout.addWidget(self.progress_bar)

    def set_loading(self, loading):
        self.progress_bar.setVisible(loading)
        self.tabs.setEnabled(not loading)
        self.test_status_btn.setEnabled(not loading)

    # --- Text Print Tab ---
    def init_text_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("输入要打印的文本："))
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("在这里输入你想打印的内容...")
        layout.addWidget(self.text_input)

        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel("字号 (8-72):"))
        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 72)
        self.font_spin.setValue(26)
        opt_layout.addWidget(self.font_spin)
        
        self.print_text_btn = QPushButton("开始打印")
        self.print_text_btn.clicked.connect(self.print_text)
        opt_layout.addWidget(self.print_text_btn)

        layout.addLayout(opt_layout)
        self.tabs.addTab(widget, "📝 文本打印")

    # --- Image & QR Tab ---
    def init_image_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # Left Column: Image
        img_box = QGroupBox("图片打印")
        img_layout = QVBoxLayout(img_box)
        self.img_path_label = QLabel("未选择文件")
        self.img_path_label.setWordWrap(True)
        img_layout.addWidget(self.img_path_label)

        self.select_img_btn = QPushButton("选择图片")
        self.select_img_btn.clicked.connect(self.select_image)
        img_layout.addWidget(self.select_img_btn)

        img_layout.addWidget(QLabel("二值化模式："))
        self.img_mode_combo = QComboBox()
        self.img_mode_combo.addItems(["floyd (照片/渐变)", "adaptive (线稿/文档)"])
        img_layout.addWidget(self.img_mode_combo)

        self.print_img_btn = QPushButton("打印图片")
        self.print_img_btn.clicked.connect(self.print_image)
        self.print_img_btn.setEnabled(False)
        img_layout.addWidget(self.print_img_btn)
        layout.addWidget(img_box)

        # Right Column: QR Code
        qr_box = QGroupBox("二维码打印")
        qr_layout = QVBoxLayout(qr_box)
        qr_layout.addWidget(QLabel("输入网址或文本："))
        self.qr_input = QLineEdit()
        self.qr_input.setPlaceholderText("https://...")
        qr_layout.addWidget(self.qr_input)

        self.print_qr_btn = QPushButton("生成并打印二维码")
        self.print_qr_btn.clicked.connect(self.print_qrcode)
        qr_layout.addWidget(self.print_qr_btn)
        
        qr_layout.addStretch()
        layout.addWidget(qr_box)

        self.tabs.addTab(widget, "🖼️ 图片与二维码")

    # --- Fun Prints Tab ---
    def init_fun_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("一键抓取并打印好玩的内容："))

        btn_layout = QHBoxLayout()
        
        btn_ff = QPushButton("💻 System Specs\n(Fastfetch)")
        btn_ff.clicked.connect(lambda: self.print_fun_content("fastfetch"))
        btn_layout.addWidget(btn_ff)

        btn_wt = QPushButton("🌦️ Weather Report\n(wttr.in)")
        btn_wt.clicked.connect(lambda: self.print_fun_content("weather"))
        btn_layout.addWidget(btn_wt)

        btn_cal = QPushButton("📅 Calendar\n(本月日历)")
        btn_cal.clicked.connect(lambda: self.print_fun_content("cal"))
        btn_layout.addWidget(btn_cal)

        btn_jk = QPushButton("🤪 Programmer Joke\n(冷笑话)")
        btn_jk.clicked.connect(lambda: self.print_fun_content("joke"))
        btn_layout.addWidget(btn_jk)

        layout.addLayout(btn_layout)

        self.fun_preview = QTextEdit()
        self.fun_preview.setReadOnly(True)
        self.fun_preview.setPlaceholderText("点击上方按钮将立即抓取、预览并发送打印...")
        layout.addWidget(self.fun_preview)

        self.tabs.addTab(widget, "🎉 好玩命令")

    # --- Settings Tab ---
    def init_config_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        cfg_box = QGroupBox("串口设置")
        cfg_layout = QVBoxLayout(cfg_box)
        
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("选择喵喵机串口："))
        self.port_combo = QComboBox()
        self.refresh_ports()
        port_layout.addWidget(self.port_combo)
        
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.clicked.connect(self.refresh_ports)
        port_layout.addWidget(refresh_btn)
        cfg_layout.addLayout(port_layout)

        save_btn = QPushButton("保存为默认串口")
        save_btn.clicked.connect(self.save_port)
        cfg_layout.addWidget(save_btn)
        
        layout.addWidget(cfg_box)

        # Paper Control Box
        ctrl_box = QGroupBox("硬件控制")
        ctrl_layout = QHBoxLayout(ctrl_box)
        
        self.selftest_btn = QPushButton("打印自检测试页")
        self.selftest_btn.clicked.connect(self.print_selftest)
        ctrl_layout.addWidget(self.selftest_btn)

        feed_layout = QHBoxLayout()
        feed_layout.addWidget(QLabel("走纸长度:"))
        self.feed_spin = QSpinBox()
        self.feed_spin.setRange(50, 1000)
        self.feed_spin.setValue(250)
        feed_layout.addWidget(self.feed_spin)
        
        feed_btn = QPushButton("立即走纸")
        feed_btn.clicked.connect(self.feed_paper)
        feed_layout.addWidget(feed_btn)
        ctrl_layout.addLayout(feed_layout)
        
        layout.addWidget(ctrl_box)
        layout.addStretch()

        self.tabs.addTab(widget, "⚙️ 设置与控制")

    # --- Slot Actions ---
    def refresh_ports(self):
        self.port_combo.clear()
        ports = list_serial_ports()
        cfg = setup_config()
        current_port = cfg.get("serial_port")
        
        for device, desc in ports:
            self.port_combo.addItem(f"{device} ({desc})", device)
            if device == current_port:
                self.port_combo.setCurrentIndex(self.port_combo.count() - 1)

    def save_port(self):
        selected_port = self.port_combo.currentData()
        if selected_port:
            cfg = setup_config()
            cfg["serial_port"] = selected_port
            save_config(cfg)
            QMessageBox.information(self, "成功", f"默认串口已更新为: {selected_port}")
        else:
            QMessageBox.warning(self, "错误", "请选择有效的串口！")

    def test_connection(self):
        self.set_loading(True)
        self.status_label.setText("🔋 状态: 正在测试连接...")
        self.worker = PrinterWorker("status")
        self.worker.finished.connect(self.on_status_finished)
        self.worker.start()

    def on_status_finished(self, success, message):
        self.set_loading(False)
        if success:
            self.status_label.setText(f"🔋 状态: 已连接 | {message.replace(chr(10), ' | ')}")
            self.status_label.setStyleSheet("font-weight: bold; color: #4caf50;")
        else:
            self.status_label.setText("🔋 状态: 连接失败")
            self.status_label.setStyleSheet("font-weight: bold; color: #f44336;")
            QMessageBox.warning(self, "连接失败", message)

    def print_text(self):
        text = self.text_input.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "输入空白", "请输入点什么再打印吧。")
            return
        self.set_loading(True)
        self.worker = PrinterWorker("text", text=text, font_size=self.font_spin.value())
        self.worker.finished.connect(self.on_print_finished)
        self.worker.start()

    def select_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.img_path_label.setText(path)
            self.print_img_btn.setEnabled(True)

    def print_image(self):
        path = self.img_path_label.text()
        mode_text = self.img_mode_combo.currentText()
        mode = "floyd" if "floyd" in mode_text else "adaptive"
        self.set_loading(True)
        self.worker = PrinterWorker("image", path=path, mode=mode)
        self.worker.finished.connect(self.on_print_finished)
        self.worker.start()

    def print_qrcode(self):
        content = self.qr_input.text().strip()
        if not content:
            QMessageBox.warning(self, "输入空白", "请输入二维码内容！")
            return
        self.set_loading(True)
        self.worker = PrinterWorker("qrcode", content=content)
        self.worker.finished.connect(self.on_print_finished)
        self.worker.start()

    def feed_paper(self):
        self.set_loading(True)
        self.worker = PrinterWorker("feed", length=self.feed_spin.value())
        self.worker.finished.connect(self.on_print_finished)
        self.worker.start()

    def print_selftest(self):
        self.set_loading(True)
        self.worker = PrinterWorker("selftest")
        self.worker.finished.connect(self.on_print_finished)
        self.worker.start()

    def on_print_finished(self, success, message):
        self.set_loading(False)
        if not success:
            QMessageBox.critical(self, "打印失败", message)
        else:
            self.status_label.setText("🔋 状态: 打印完成")
            self.status_label.setStyleSheet("font-weight: bold; color: #4caf50;")

    # --- Fun Content Async Fetch & Print ---
    def print_fun_content(self, type_name):
        self.set_loading(True)
        self.fun_preview.setText("正在获取内容...")
        
        # Async fetch content to prevent UI freezing
        class FetchWorker(QThread):
            fetched = Signal(str)
            def __init__(self, t):
                super().__init__()
                self.t = t
            def run(self):
                if self.t == "fastfetch":
                    try:
                        res = subprocess.run(["fastfetch", "--pipe"], capture_output=True, text=True, check=True)
                        self.fetched.emit(res.stdout)
                    except Exception as e:
                        self.fetched.emit(f"获取 specs 失败: {e}")
                elif self.t == "weather":
                    try:
                        req = urllib.request.Request("http://wttr.in?0&T", headers={"User-Agent": "curl/7.79.1"})
                        with urllib.request.urlopen(req, timeout=5) as response:
                            self.fetched.emit(response.read().decode('utf-8'))
                    except Exception as e:
                        self.fetched.emit(f"获取天气失败: {e}")
                elif self.t == "cal":
                    try:
                        res = subprocess.run(["cal"], capture_output=True, text=True, check=True)
                        self.fetched.emit(res.stdout)
                    except Exception as e:
                        self.fetched.emit(f"获取日历失败: {e}")
                elif self.t == "joke":
                    try:
                        url = "https://v2.jokeapi.dev/joke/Programming?type=single&safe-mode"
                        req = urllib.request.Request(url, headers={"User-Agent": "python-urllib"})
                        with urllib.request.urlopen(req, timeout=5) as response:
                            data = json.loads(response.read().decode('utf-8'))
                            self.fetched.emit(data.get("joke", "无笑话"))
                    except Exception as e:
                        self.fetched.emit(f"获取笑话失败: {e}")

        self.fetcher = FetchWorker(type_name)
        
        def on_fetched(text):
            self.fun_preview.setText(text)
            # Send to printer worker
            font_size = 15 if type_name == "fastfetch" else (22 if type_name == "weather" else 26)
            self.worker = PrinterWorker("text", text=text, font_size=font_size)
            self.worker.finished.connect(self.on_print_finished)
            self.worker.start()

        self.fetcher.fetched.connect(on_fetched)
        self.fetcher.start()


# --- Main ---
def main():
    app = QApplication(sys.argv)
    gui = PaperangGUI()
    gui.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
