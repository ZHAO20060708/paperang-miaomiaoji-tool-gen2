import json
import os
import serial.tools.list_ports

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "serial_port": None,
    "baudrate": 115200,
    "timeout": 1
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return {**DEFAULT_CONFIG, **cfg}
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    return [(p.device, f"{p.description}") for p in ports]


def setup_config():
    cfg = load_config()
    if cfg.get("serial_port"):
        return cfg

    print("首次启动，未找到串口配置。")
    ports = list_serial_ports()
    if not ports:
        print("未检测到可用串口，请检查设备连接后重试。")
        raise RuntimeError("No serial ports available")

    print("\n可用串口列表：")
    for idx, (device, desc) in enumerate(ports, 1):
        print(f"  {idx}. {device} - {desc}")

    while True:
        try:
            choice = int(input("\n请选择串口编号: ").strip())
            if 1 <= choice <= len(ports):
                selected = ports[choice - 1][0]
                break
            else:
                print("输入无效，请重新选择。")
        except ValueError:
            print("请输入数字编号。")

    cfg["serial_port"] = selected
    save_config(cfg)
    print(f"已保存配置: {selected} -> {CONFIG_FILE}\n")
    return cfg
