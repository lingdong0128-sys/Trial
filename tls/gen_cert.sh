#!/bin/bash
# 在 tls/ 目录下生成自签名证书，供 Flask HTTPS 使用
# 运行: bash gen_cert.sh 或 ./gen_cert.sh（需 chmod +x）
cd "$(dirname "$0")"
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
  -subj "/CN=localhost/O=Trial"
echo "已生成 tls/cert.pem 与 tls/key.pem，重启应用后将自动使用。"
