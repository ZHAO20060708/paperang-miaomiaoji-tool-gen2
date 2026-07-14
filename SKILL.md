---
name: paperang
description: >-
  控制喵喵机2（Paperang Gen2）蓝牙热敏打印机。支持打印文字、图片、二维码，
  查询状态（电池/序列号/硬件），走纸、自检、配置串口。
  触发词：打印、printer、paperang、喵喵机、打印文字、打印图片、打印二维码、走纸、
  selftest、热敏、thermal print。确保在用户提到任何与打印相关的需求时使用此 skill。
---

# Paperang 2 喵喵机打印 Skill

## 核心规则

1. **串口先行** — 执行任何打印前必须确认串口已配置。检查方法：`paperang config`。如果 `serial_port` 为 null，必须引导用户完成配置，绝不猜测串口。
2. **走纸收尾** — 单次打印后加 `--feed 250` 把内容推出机器。连续多条打印时中间不走纸，最后一条加 `--feed 250` 或追加 `paperang feed 250`。忘记走纸 = 内容卡在机器里看不到。
3. **确认文件存在** — 打印图片前先确认文件路径有效。

## 命令速查

> 如果项目已通过 `uv tool install` 或 `pip install` 全局安装，直接使用 `paperang`。
> 否则在项目目录下使用 `uv run python -m paperang`。

| 任务 | 命令 |
|---|---|
| 查看配置 | `paperang config` |
| 列出串口 | `paperang config --list` |
| 设置串口 | `paperang config --set-port /dev/rfcomm0` |
| 打印文字 | `paperang text "你好世界"` |
| 打印文字（大号） | `paperang text --font-size 48 "标题"` |
| 打印文字（自定义字体） | `paperang text --font "/path/to/font.ttf" "内容"` |
| 打印图片 | `paperang image photo.jpg` |
| 打印图片（文档模式） | `paperang image --mode adaptive doc.png` |
| 打印图片（禁用旋转） | `paperang image --no-rotate wide.png` |
| 打印二维码 | `paperang qrcode "https://example.com"` |
| 查询状态（全部） | `paperang status` |
| 查询电池 | `paperang status --battery` |
| 自检页 | `paperang selftest` |
| 走纸 | `paperang feed 250` |
| 降低浓度打印 | `paperang -d 60 text "省墨"` |
| 临时指定串口 | `paperang -p /dev/rfcomm1 text "hello"` |

## 全局参数

所有连接打印机的子命令均支持：

| 参数 | 说明 |
|---|---|
| `-p PORT` / `--port PORT` | 临时指定串口（不修改配置文件） |
| `-d N` / `--density N` | 打印浓度 1–100（默认 100） |

## 子命令参数详情

### text

```
paperang text [--font-size N] [--font PATH] [--feed N] "内容"
```

- `--font-size`：字体大小，默认 24。推荐范围 12–72。
- `--font`：自定义字体文件路径（.ttf/.otf）或系统字体名称。不指定则使用内置 MapleMono 等宽字体。
- `--feed`：打印后走纸长度。
- 支持 `\n` 换行、`\t` 制表符。

字号参考：

| 字号 | 适用 |
|---|---|
| 12–24 | 密集文本、长段落（默认） |
| 36 | 中等，兼顾可读性与信息量 |
| 48 | 大字，标题或重点 |
| 72 | 超大，短句或展示 |

### image

```
paperang image [--mode floyd|adaptive|auto] [--no-rotate] [--feed N] PATH
```

| 模式 | 算法 | 适用场景 |
|---|---|---|
| `floyd`（默认） | Floyd-Steinberg 误差扩散 | 照片、渐变、连续色调 |
| `adaptive` | 局部自适应阈值 | 文档、线稿、高对比度 |
| `auto` | 自动选择 | 不确定时使用 |

图片自动缩放至 576px 宽，横向图片默认旋转为纵向（`--no-rotate` 禁用）。

### qrcode

```
paperang qrcode [--feed N] "内容"
```

### status

```
paperang status [--battery] [--sn] [--hardware]
```

不带参数查询全部。

### feed / selftest

```
paperang feed <长度>
paperang selftest
```

---

## 工作流程

每次打印任务按以下步骤执行：

1. **确认串口** — 运行 `paperang config`，有 `serial_port` 则继续，否则走首次设置流程。
2. **确认意图** — 用户要打印什么？收集内容、字号、图片路径等参数。
3. **执行命令** — 构建并运行命令。连续打印用 `&&` 串联，最后一条带走纸。
4. **报告结果** — 告诉用户执行情况。

### 连续打印示例

```bash
paperang text --font-size 36 "标题" && \
paperang qrcode "https://example.com" && \
paperang text "扫码访问" --feed 250
```

---

## 首次设置

仅需执行一次，端口配置持久保存在项目的 `config.json` 中。

1. **安装依赖**（如尚未安装）：
   ```bash
   uv sync
   ```

2. **蓝牙配对**：
   - 长按喵喵机电源键至指示灯闪烁
   - 系统蓝牙设置中配对名称含 PAPERANG 的设备
   - Linux 可能需要手动绑定：`sudo rfcomm bind 0 <MAC地址>`

3. **选择串口**：
   ```bash
   paperang config --list
   ```
   展示列表，询问用户："哪个是你的喵喵机串口？"

4. **保存配置**：
   ```bash
   paperang config --set-port /dev/rfcomm0
   ```

5. **验证连接**：
   ```bash
   paperang text --font-size 32 "测试打印" --feed 250
   ```

配置完成后写入持久记忆，后续会话无需重复。

## 故障排查

| 问题 | 处理 |
|---|---|
| 连接失败 | `paperang config --list` 确认串口存在；检查打印机是否开机并已配对 |
| 串口消失 | 可能需要重新 `sudo rfcomm bind`；询问用户重新选择 |
| 打印出来是空白 | 忘记走纸，补一个 `paperang feed 250` |
| 图片效果差 | 照片用 `floyd`，文档/线稿用 `adaptive` |

## 注意事项

- 不要硬编码串口号，始终从配置读取或让用户选择
- 不要在未确认文件存在的情况下打印图片
- 不要跳过配置检查
- 使用 `uv sync` 安装依赖，不要全局 pip install 到系统 Python
