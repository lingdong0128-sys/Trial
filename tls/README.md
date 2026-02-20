# TLS 证书目录

本目录用于存放 HTTPS 自签名证书。应用启用 HTTPS 时会优先使用此处的 `cert.pem` 与 `key.pem`。

## 生成证书

在项目根目录或本目录下执行：

```bash
bash tls/gen_cert.sh
```

或进入本目录后执行：

```bash
cd tls && bash gen_cert.sh
```

将生成：

- `cert.pem`：证书
- `key.pem`：私钥（请勿提交到版本库）

生成后重启 `python app.py`，即可使用 `tls/` 下的证书提供 HTTPS。
