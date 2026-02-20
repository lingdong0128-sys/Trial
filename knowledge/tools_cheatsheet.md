# 工具速查

## 信息收集

### nmap
- 基础扫描：`nmap -sV -sC target`
- 全端口：`nmap -p- target`
- UDP 扫描：`nmap -sU target`
- 脚本扫描：`nmap --script vuln target`
- 规避防火墙：`nmap -T2 -f --script-timeout 30s target`

### dirb/dirsearch
- 目录爆破：`dirsearch -u http://target -e php,html,txt`
- 自定义字典：`-w /path/to/wordlist`

### whatweb
- 识别 Web 技术：`whatweb http://target`

## Web 漏洞

### sqlmap
- 基础注入：`sqlmap -u "http://target?id=1" --dbs`
- POST 注入：`sqlmap -r request.txt`
- 绕过 WAF：`--tamper=space2comment,randomcase`
- 获取 shell：`--os-shell`

### burpsuite
- Repeater：手动测试
- Intruder：爆破/模糊测试
- Scanner：自动漏洞扫描
- Collaborator：带外检测

### ffuf
- 目录爆破：`ffuf -w wordlist -u http://target/FUZZ`
- 多参数：`-u http://target?param=FUZZ&other=TEST`
- 过滤响应：`-fc 404 -fs 0`

## 二进制分析

### gdb
- 加载：`gdb ./binary`
- 断点：`b *main`, `b main`
- 运行：`r < input`
- 查看内存：`x/10gx $rsp`
- 寄存器：`info registers`

### pwndbg
- heap 分析：`heap`, `bins`
- ROP：`rop`, `stack`
- 内存：`vmmap`, `telescope`

### radare2
- 分析：`r2 -A binary`
- 反编译：`af; pdf @ main`
- 搜索：`/ string`

## 密码学

### john
- 破解哈希：`john hash.txt --wordlist=rockyou.txt`
- 格式指定：`--format=raw-md5`

### hashcat
- GPU 破解：`hashcat -m 0 hash.txt rockyou.txt`
- 模式：`-a 0` (字典), `-a 3` (掩码)

### openssl
- 解密：`openssl enc -d -aes-256-cbc -in file -out dec`
- 生成密钥：`openssl rand -hex 32`

## 取证隐写

### binwalk
- 分析：`binwalk file`
- 提取：`binwalk -e file`
- 熵分析：`binwalk -E file`

### steghide
- 提取：`steghide extract -sf image.jpg`
- 无密码：直接回车

### exiftool
- 查看：`exiftool image.jpg`
- 删除：`exiftool -all= image.jpg`

## 网络分析

### wireshark/tshark
- 过滤 HTTP：`http.request.method == "GET"`
- 提取文件：`File → Export Objects`
- 命令行：`tshark -r capture.pcap -Y "http" -T fields -e http.host`

### tcpdump
- 抓包：`tcpdump -i eth0 -w capture.pcap`
- 过滤：`tcpdump port 80`

## 编码转换

### xxd
- 十六进制：`xxd file`
- 反向：`xxd -r hexfile > binary`

### base64
- 编码：`base64 file`
- 解码：`base64 -d file`

### CyberChef
- 在线工具：https://gchq.github.io/CyberChef/
- 支持数百种操作

## 自动化

### pwntools
- 连接：`p = remote('host', port)`
- 打包：`p64(addr)`, `p32(addr)`
- 交互：`p.interactive()`

### requests (Python)
- GET：`requests.get(url, params=params)`
- POST：`requests.post(url, data=data)`
- 会话：`s = requests.Session()`

## 杂项

### strings
- 提取文本：`strings -n 8 file`
- 编码指定：`strings -e l file` (little-endian)

### file
- 识别类型：`file suspicious_file`

### grep
- 递归搜索：`grep -r "flag" .`
- 正则：`grep -E "flag\{.*\}" file`

### find
- 按类型：`find . -name "*.txt"`
- 按内容：`find . -exec grep -l "flag" {} \;`