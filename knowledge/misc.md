# 杂项 (Misc)

## 编码与转换

### 常见编码
- **Base64**: `echo "text" | base64` / `base64 -d`
- **Base32**: Python `base64.b32encode()`
- **Base58**: Bitcoin 地址，需专用库
- **Hex**: `xxd -p` / `xxd -r -p`
- **URL 编码**: `%20` = space, `%0A` = newline
- **HTML 实体**: `&lt;` = `<`, `&#x41;` = A

### 进制转换
- 二进制 ↔ 十六进制: `printf '%x\n' "$((2#101010))"`
- 十进制 ↔ ASCII: `python3 -c "print(chr(65))"` → A
- 浮点数 IEEE 754: 在线转换工具或 Python struct

### 编码识别
- **CyberChef**：自动尝试多种编码
- **binwalk -E**：熵分析检测加密/编码
- 特征字符串：`==` (Base64), `=` (Base32), 只有 0-9A-V (Base32)

## 协议分析

### 网络流量 (PCAP)
- **Wireshark**：过滤语法 `tcp.port==80`
- **tshark**：命令行版 Wireshark
- 常见提取：
  - HTTP 文件：`File → Export Objects → HTTP`
  - DNS 隧道：检查长域名
  - FTP 传输：查看数据流

### USB 流量
- **wireshark**：USB capture 解析
- **usbpcap**：Windows USB 抓包
- 键盘流量：HID 数据转按键

### 蓝牙/NFC
- **Ubertooth**：蓝牙嗅探
- **Proxmark3**：NFC 分析

## 自动化脚本

### Python 常用库
- **requests**：HTTP 请求
- **pwntools**：网络交互、打包数据
- **Pillow**：图片处理
- **pycryptodome**：密码学操作
- **scapy**：网络包构造

### Bash 技巧
- 并行处理：`parallel`
- 循环爆破：`for i in {0000..9999}; do ...; done`
- 条件判断：`if [[ $(curl ...) == *"flag"* ]]; then ...`

### 常用命令组合
```bash
# 提取所有 IP
grep -oE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" file

# 查找可打印字符串中的 flag
strings file | grep -i "flag{"

# 十六进制转文本
xxd -r -p hex.txt > output

# Base64 递归解码
while file encoded | grep -q "ASCII text"; do
    base64 -d encoded > decoded && mv decoded encoded
done
```

## 其他技巧

### Git 泄露
- 访问 `.git/` 目录
- 使用 `git log` 查看历史
- `git show <commit>:<file>` 恢复文件
- 工具：`git-dumper`, `GitHack`

### Docker 安全
- 挂载 `/var/run/docker.sock` → 逃逸
- 检查环境变量：`env`
- 查看挂载点：`mount`

### 时间戳转换
- Unix 时间戳：`date -d @1609459200`
- Windows FILETIME：Python 转换

### QR Code
- **zbarimg**: `zbarimg qr.png`
- 损坏修复：GIMP 修复定位图案
- 动态 QR：视频帧提取

## CTF 解题流程
1. **信息收集**：`file`, `strings`, `binwalk`, `exiftool`
2. **识别类型**：根据特征判断编码/加密/隐写
3. **尝试常见方法**：按知识库顺序测试
4. **自动化**：编写脚本批量处理
5. **深入分析**：逆向/协议解析/数学分析