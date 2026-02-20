# 密码学

## 古典密码

### 凯撒密码 (Caesar Cipher)
- 位移固定：`plaintext[i] = (ciphertext[i] - key) % 26`
- 爆破：尝试所有 25 种位移

### 维吉尼亚密码 (Vigenère Cipher)
- 多表替换，密钥重复使用
- **Kasiski 测试**：找重复序列确定密钥长度
- **重合指数 (IC)**：验证密钥长度
- 单表频率分析破解每个子密钥

### 栅栏密码 (Rail Fence)
- 按行写入，按列读出
- 爆破行数

### 摩斯电码
- `.-` = A, `-...` = B, etc.
- 常见变体：数字、标点

## 现代密码

### 对称加密
- **AES**：ECB/CBC/CTR 模式
  - ECB 不安全（相同明文→相同密文）
  - CBC 需要 IV，可 padding oracle 攻击
- **DES/3DES**：已不安全
- **RC4**：流密码，有偏差

### 非对称加密
- **RSA**：
  - 公钥 (n, e)，私钥 (n, d)
  - 常见攻击：
    - 小公钥指数 e=3 + 无填充 → 直接开立方
    - 共模攻击：相同 n，不同 e
    - 低解密指数攻击 (Wiener)
    - p 和 q 接近 → Fermat 分解
    - 已知 p 或 q 的部分位 → Coppersmith
- **ECC**：椭圆曲线，参数需验证

### 哈希函数
- **MD5**：已完全碰撞
- **SHA1**：理论碰撞
- **SHA2/SHA3**：目前安全
- **Length Extension Attack**：针对 Merkle-Damgård 结构（MD5, SHA1, SHA2）

## 常见攻击

### Padding Oracle
- CBC 模式下，通过 padding 正确性判断逐字节解密
- 工具：`padbuster`

### RSA 共模攻击
```python
# 已知 c1 = m^e1 mod n, c2 = m^e2 mod n, gcd(e1,e2)=1
s1 = inverse(e1, e2)
s2 = (gcd(e1,e2) - e1*s1) // e2
m = (pow(c1,s1,n) * pow(c2,s2,n)) % n
```

### LSB Oracle
- 逐位泄露明文最低位
- 适用于 RSA 且能查询 (c * 2^e mod n) 的解密结果

### 弱随机数
- 重复使用 nonce（如 ECDSA）
- 伪随机数预测

## 编码与转换

### Base 系列
- Base64：`ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/`
- Base32：`ABCDEFGHIJKLMNOPQRSTUVWXYZ234567`
- Base58：比特币地址，去除了 0OIl

### 进制转换
- 二进制 ↔ 十六进制 ↔ 十进制
- ASCII ↔ 十六进制

### 工具
- CyberChef：在线编码/解码
- RsaCtfTool：自动化 RSA 攻击
- HashExtender：Length Extension 攻击

## 解题思路
1. 识别加密类型（文件头、特征字符串）
2. 检查参数是否弱（小素数、重复 nonce）
3. 尝试常见攻击（共模、小指数、padding oracle）
4. 对于未知算法，分析代码或逆向