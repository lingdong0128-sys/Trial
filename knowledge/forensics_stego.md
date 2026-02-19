# 取证与隐写

## 文件分析

### 文件头识别
- **JPEG**: `FF D8 FF`
- **PNG**: `89 50 4E 47 0D 0A 1A 0A`
- **ZIP**: `50 4B 03 04`
- **PDF**: `%PDF-`
- **ELF**: `7F 45 4C 46`

### 工具
- `file`：识别文件类型
- `binwalk`：固件/文件系统分析
- `foremost` / `photorec`：文件恢复
- `exiftool`：查看元数据

### 内存取证
- **Volatility**：分析内存转储
  - `imageinfo`：确定 profile
  - `pslist`：进程列表
  - `dumpfiles`：导出文件
  - `hashdump`：提取密码哈希

## 图片隐写

### LSB (最低有效位)
- 修改像素最低位隐藏信息
- 工具：
  - `stegsolve.jar`：可视化分析
  - `zsteg`：PNG/BMP LSB 分析
  - `steghide`：密码保护隐写

### 其他技术
- **DCT 系数**：JPEG 频域隐写
- **调色板**：GIF 颜色索引
- **EXIF 数据**：隐藏文本

### 检测方法
- **卡方分析**：检测 LSB 隐写
- **RS 分析**：统计检测
- **直方图分析**：异常分布

## 音频隐写

### 方法
- LSB 音频样本
- 回声隐藏
- 相位编码

### 工具
- **Audacity**：波形/频谱分析
- **Sonic Visualiser**：高级音频分析
- **deepsound**：专用隐写工具

## 其他隐写

### 文本隐写
- 零宽字符（ZWSP, ZWNJ）
- 空格/制表符编码
- 同形字符（Unicode homoglyphs）

### 协议隐写
- ICMP 隧道
- DNS 隧道
- HTTP 头部隐藏

## 常见 CTF 技巧

### ZIP 相关
- 伪加密：修改加密标志位
- 明文攻击：已知部分明文
- CRC32 爆破：小文件内容
- 注释隐藏：`zip -z file.zip`

### PDF 分析
- 对象流解压：`qpdf --stream-data=uncompress`
- JavaScript 提取：`pdf-parser.py -s JS`
- 隐藏图层：Acrobat 查看

### 磁盘镜像
- `fdisk -l image.img`：分区信息
- `mount -o loop,offset=...`：挂载分区
- `strings` + `grep`：快速搜索

## 自动化脚本

### 提取所有字符串
```bash
strings -n 8 suspicious_file | grep -E "flag|ctf|key"
```

### 检查文件尾部
```bash
xxd file | tail -20
```

### 自动化隐写检测
```python
import subprocess
def check_stego(file):
    # LSB
    result = subprocess.run(['zsteg', file], capture_output=True, text=True)
    if 'imagedata' in result.stdout:
        print("LSB detected!")
    # Steghide
    result = subprocess.run(['steghide', 'info', file], input='\n', capture_output=True, text=True)
    if 'embedded data' in result.stdout:
        print("Steghide detected!")
```