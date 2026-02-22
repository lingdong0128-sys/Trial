# Mitmproxy 集成实现文档

## 1. 概述

本项目集成了 Mitmproxy 作为 HTTP(S) 代理服务器，实现了流量拦截、修改、录制和 HTTPS 解密功能。该集成通过 Flask Web 应用提供用户界面，并通过 UTCP（Unified Tool Control Protocol）协议与 AI 模型交互，允许 AI 动态控制网络流量。

### 核心功能

- **流量录制**：记录所有经过代理的 HTTP/HTTPS 请求和响应
- **HTTPS 解密**：支持 HTTPS 流量的解密和查看
- **流量拦截**：通过正则表达式匹配 URL，执行不同的拦截规则
- **动态修改**：实时修改请求头、响应体或阻断请求
- **AI 集成**：通过 UTCP 协议让 AI 控制流量拦截规则

---

## 2. 架构设计

### 2.1 系统组件

```
┌─────────────────────────────────────────────────────────────┐
│                        Flask Web 应用                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   路由层      │  │   UTCP 层     │  │   UI 界面     │      │
│  │ routes/      │  │ utcp/        │  │ templates/   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        服务层                                │
│  ┌──────────────────┐  ┌──────────────────┐                  │
│  │ MitmProxyService │  │TrafficRuleManager│                  │
│  │ (核心代理服务)    │  │  (规则管理器)     │                  │
│  └──────────────────┘  └──────────────────┘                  │
│  ┌──────────────────┐  ┌──────────────────┐                  │
│  │BrowserSession    │  │BrowserPackets    │                  │
│  │(会话管理)        │  │(数据包存储)       │                  │
│  └──────────────────┘  └──────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      Mitmproxy 核心                          │
│  ┌────────────────────────────────────────────────────┐     │
│  │           AIInterceptorAddon (自定义插件)            │     │
│  │  - request(): 请求阶段拦截                           │     │
│  │  - response(): 响应阶段拦截                           │     │
│  └────────────────────────────────────────────────────┘     │
│  ┌────────────────────────────────────────────────────┐     │
│  │              DumpMaster (代理核心)                   │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流向

```
用户浏览器 
    │ (配置代理到 127.0.0.1:8888)
    ▼
Mitmproxy 代理
    │
    ├─── request() 阶段 ───▶ TrafficRuleManager.match_rules()
    │                             │
    │                             ├─── 修改请求头
    │                             ├─── 阻断请求
    │                             └─── 转发请求
    │
    ▼
目标服务器
    │
    ▼ 响应
    │
    ├─── response() 阶段 ───▶ TrafficRuleManager.match_rules()
    │                               │
    │                               ├─── 修改响应体
    │                               └─── 录制数据包
    │                                   ▼
    │                           BrowserPackets.add_packet()
    │                                   │
    │                                   ▼
    │                           内存存储 + JSON 文件
    │
    ▼
返回给浏览器
```

---

## 3. 核心模块详解

### 3.1 MitmProxyService (services/mitm_service.py)

#### 功能描述
Mitmproxy 代理服务的封装类，管理代理的启动和停止，在独立线程中运行。

#### 关键特性

1. **异步事件循环**：在独立线程中运行 asyncio 事件循环
2. **插件系统集成**：通过 `AIInterceptorAddon` 实现自定义流量拦截逻辑
3. **日志隔离**：禁用 Mitmproxy 的所有日志，避免与 Flask 的 Werkzeug 日志冲突

#### 代码结构

```python
class MitmProxyService:
    def __init__(self, host="127.0.0.1", port=8080):
        """初始化服务，设置监听地址和端口"""
        
    def start(self) -> int:
        """启动代理服务，返回实际监听的端口号"""
        
    def _run_loop(self):
        """在独立线程中运行 Mitmproxy 事件循环"""
        
    def stop(self):
        """停止代理服务"""
        
    @property
    def proxy_url(self) -> str:
        """获取代理 URL，如 http://127.0.0.1:8080"""
```

#### 实现细节

- **线程安全**：使用 `threading.Thread` 在独立线程中运行
- **端口管理**：默认监听 127.0.0.1:8080，可在 browser_session.py 中配置为 8888
- **优雅关闭**：通过 `master.shutdown()` 实现优雅停止

---

### 3.2 AIInterceptorAddon (services/mitm_service.py)

#### 功能描述
Mitmproxy 的自定义插件，负责流量拦截规则的执行和数据包的录制。

#### 拦截阶段

```python
class AIInterceptorAddon:
    def request(self, flow: http.HTTPFlow):
        """请求阶段处理"""
        # 1. 执行请求阶段的拦截规则
        # 2. 支持的操作：
        #    - 修改请求头
        #    - 阻断请求
        
    def response(self, flow: http.HTTPFlow):
        """响应阶段处理"""
        # 1. 执行响应阶段的拦截规则
        # 2. 支持的操作：
        #    - 修改响应体
        # 3. 录制数据包到 BrowserPackets 存储
```

#### 支持的拦截规则类型

| 规则类型 | 阶段 | 说明 |
|---------|------|------|
| `modify_request_header` | request | 修改请求头 |
| `block_request` | request | 阻断请求 |
| `modify_response_body` | response | 修改响应体 |

---

### 3.3 TrafficRuleManager (services/traffic_rules.py)

#### 功能描述
流量规则管理器，使用单例模式存储和管理 AI 下发的流量拦截规则。

#### 核心方法

```python
class TrafficRuleManager:
    def add_rule(self, rule_type: str, url_regex: str, action_data: dict) -> str:
        """添加新的流量拦截规则，返回规则 ID"""
        
    def get_rules(self) -> List[Dict]:
        """获取所有规则列表"""
        
    def clear_rules(self):
        """清空所有规则"""
        
    def match_rules(self, flow, phase: str) -> List[Dict]:
        """根据请求/响应匹配适用的规则"""
```

#### 规则数据结构

```python
rule = {
    "id": "1",                    # 规则 ID
    "type": "modify_request_header",  # 规则类型
    "regex": "example.com/api",   # URL 匹配正则表达式
    "data": {                     # 规则执行所需数据
        "key": "Authorization",
        "value": "Bearer token123"
    },
    "enabled": True               # 是否启用
}
```

#### 匹配逻辑

- 使用正则表达式匹配 URL
- 根据阶段过滤规则类型
- 支持规则的启用/禁用状态

---

### 3.4 BrowserSession (services/browser_session.py)

#### 功能描述
录制代理的单例管理器，负责代理的启动、停止和状态查询。

#### 核心功能

```python
def ensure_proxy_started():
    """确保代理已启动（懒加载模式）"""
    # 使用固定端口 8888，方便用户配置
    
def get_proxy_url():
    """获取当前代理 URL"""
    
def get_proxy_port():
    """获取当前代理端口"""
    
def get_mitmproxy_cert_path():
    """获取 Mitmproxy CA 证书路径"""
    
def stop_proxy():
    """停止代理服务"""
```

#### CA 证书处理

Mitmproxy 默认在用户目录下的 `.mitmproxy` 文件夹生成 CA 证书：
- Windows: `C:\Users\<用户名>\.mitmproxy\mitmproxy-ca-cert.pem`
- Linux/Mac: `~/.mitmproxy/mitmproxy-ca-cert.pem`

用户需要将该证书安装到浏览器/系统中并设置为"始终信任"才能解密 HTTPS 流量。

---

### 3.5 BrowserPackets (services/browser_packets.py)

#### 功能描述
流量数据包的存储和管理系统，支持内存存储和 JSON 文件持久化。

#### 核心方法

```python
def add_packet(method, url, request_headers, request_body, 
               response_status, response_headers, response_body):
    """记录一条请求/响应，body 会做截断预览"""
    
def list_packets(url_contains: str = None, limit: int = 200):
    """返回录包列表，可选按 URL 过滤"""
    
def get_packet(packet_id: str):
    """按 id 返回一条录包"""
    
def clear_packets():
    """清空所有录包"""
```

#### 数据结构

```python
{
    "id": "abc12345",              # 数据包 ID
    "time": 1678901234.567,        # 时间戳
    "method": "GET",               # 请求方法
    "url": "https://example.com/api/data",
    "request_headers": {           # 请求头
        "host": "example.com",
        "user-agent": "Mozilla/5.0..."
    },
    "request_body_preview": "...", # 请求体预览（截断）
    "response_status": 200,        # 响应状态码
    "response_headers": {          # 响应头
        "content-type": "application/json"
    },
    "response_body_preview": "..." # 响应体预览（截断）
}
```

#### 存储策略

- **内存存储**：数据包存储在内存列表中，快速访问
- **文件持久化**：自动保存到 `data/browser_packets.json`
- **数据截断**：请求体和响应体预览限制为 64KB
- **自动加载**：应用启动时从文件加载历史数据

---

### 3.6 RecordingProxy (services/recording_proxy.py)

#### 功能描述
HTTP(S) 录制代理的备选实现，不使用 Mitmproxy，提供基本的流量录制功能。

#### 主要区别

| 特性 | MitmProxyService | RecordingProxy |
|------|-----------------|----------------|
| HTTPS 解密 | ✅ 支持 | ❌ 仅记录 CONNECT |
| 流量修改 | ✅ 支持 | ❌ 不支持 |
| 性能 | 中等 | 轻量级 |
| 依赖 | mitmproxy | 仅标准库 |

#### 使用场景

- `RecordingProxy`：仅需要基本流量录制，不需要 HTTPS 解密
- `MitmProxyService`：需要完整的流量拦截和 HTTPS 解密功能

---

## 4. UTCP 集成

### 4.1 工具定义 (utcp/tools_def.py)

通过 UTCP 协议向 AI 模型暴露以下流量控制工具：

#### add_traffic_modification

添加网络流量修改规则。

```json
{
  "name": "add_traffic_modification",
  "description": "添加网络流量修改规则",
  "parameters": {
    "url_regex": "匹配 URL 的正则表达式",
    "modification_type": "修改类型",
    "data": {
      "key": "请求头键名",
      "value": "请求头值",
      "old_text": "要替换的原始文本",
      "new_text": "替换后的新文本"
    }
  }
}
```

#### clear_traffic_rules

清除所有流量拦截规则。

#### list_traffic_rules

列出所有当前的流量拦截规则。

#### list_browser_packets

列出记录器已录制的 HTTP 数据包。

#### get_browser_packet

根据 id 获取单条录包的详情。

### 4.2 工具实现 (utcp/traffic_tools.py)

```python
def add_traffic_modification(url_regex: str, modification_type: str, data: dict) -> dict:
    """添加网络流量修改规则"""
    # 参数验证
    # 调用 TrafficRuleManager.add_rule()
    # 返回执行结果
```

---

## 5. Web 界面集成

### 5.1 路由设计 (routes/browser.py)

```python
@browser_bp.route("recorder")
def recorder():
    """记录器页面：显示代理端口与 Wireshark 式数据包列表"""
    
@browser_bp.route("api/recorder/proxy", methods=["GET"])
def api_proxy():
    """返回代理地址与端口"""
    
@browser_bp.route("api/browser/packets", methods=["GET", "POST"])
def packets_list_or_clear():
    """GET：返回录包列表；POST：清空录包"""
    
@browser_bp.route("api/browser/packets/<packet_id>", methods=["GET"])
def packet_detail(packet_id):
    """返回单条录包详情"""
    
@browser_bp.route("api/recorder/cert", methods=["GET"])
def download_cert():
    """下载 Mitmproxy CA 证书"""
```

### 5.2 用户界面 (templates/recorder.html)

#### 功能特性

1. **代理信息展示**
   - 显示代理地址和端口
   - 代理状态指示

2. **数据包列表**
   - Wireshark 风格的表格展示
   - 支持按 URL 过滤
   - 显示时间、方法、URL、状态码

3. **数据包详情**
   - 请求头和请求体
   - 响应头和响应体
   - JSON 格式化

4. **证书下载**
   - 一键下载 Mitmproxy CA 证书
   - 安装指南

---

## 6. 使用流程

### 6.1 启动服务

1. 启动 Flask 应用：
   ```bash
   python app.py
   ```

2. 访问记录器页面：
   ```
   http://localhost:5000/recorder
   ```

3. 代理会自动在 127.0.0.1:8888 启动

### 6.2 配置浏览器代理

1. 打开浏览器代理设置
2. 配置 HTTP 代理：
   - 地址：127.0.0.1
   - 端口：8888
3. （可选）配置 HTTPS 代理：
   - 地址：127.0.0.1
   - 端口：8888

### 6.3 安装 CA 证书（用于 HTTPS 解密）

1. 在记录器页面下载 CA 证书
2. 安装证书到浏览器：
   - Chrome/Edge：设置 → 隐私和安全 → 安全 → 管理证书
   - Firefox：选项 → 隐私与安全 → 证书 → 查看证书
3. 将证书导入到"受信任的根证书颁发机构"
4. 标记证书为"始终信任"

### 6.4 AI 控制流量

通过对话界面，AI 可以自动调用流量控制工具：

```
用户：帮我拦截所有访问 example.com 的请求
AI：[调用 add_traffic_modification]
    已添加规则：当 URL 匹配 'example.com' 时阻断请求

用户：修改 example.com/api 的响应，将 "error" 替换为 "success"
AI：[调用 add_traffic_modification]
    已添加规则：修改响应体规则已添加
```

---

## 7. 配置说明

### 7.1 环境变量

在 `.env` 文件中可配置：

```env
# HTTPS 设置
HTTPS=1
SSL_CERT_FILE=/path/to/cert.pem
SSL_KEY_FILE=/path/to/key.pem

# Flask 配置
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=true

# 密钥
SECRET_KEY=your-secret-key
```

### 7.2 代理端口配置

默认代理端口为 8888，可在 `services/browser_session.py` 中修改：

```python
_proxy = MitmProxyService("127.0.0.1", 8888)  # 修改端口
```

---

## 8. 故障排查

### 8.1 代理无法启动

**症状**：记录器页面显示代理启动失败

**解决方案**：
1. 检查端口 8888 是否被占用
2. 查看日志输出错误信息
3. 确保 mitmproxy 已正确安装

### 8.2 HTTPS 流量无法解密

**症状**：HTTPS 请求显示为 CONNECT 方法，无法查看内容

**解决方案**：
1. 下载并安装 Mitmproxy CA 证书
2. 确保证书导入到正确的证书存储位置
3. 设置证书为"始终信任"
4. 重启浏览器

### 8.3 数据包未记录

**症状**：访问网页后记录器页面无数据

**解决方案**：
1. 确认浏览器代理配置正确
2. 检查代理服务是否正常运行
3. 清除浏览器缓存重试
4. 查看控制台日志

### 8.4 拦截规则不生效

**症状**：添加的规则未执行

**解决方案**：
1. 检查正则表达式是否正确匹配 URL
2. 使用 `list_traffic_rules` 查看规则列表
3. 确认规则类型与请求/响应阶段匹配
4. 清除规则后重新添加

---

## 9. 安全注意事项

### 9.1 证书管理

- Mitmproxy CA 证书具有解密所有 HTTPS 流量的能力
- 不要将 CA 证书泄露给他人
- 使用完毕后及时卸载证书

### 9.2 网络安全

- 代理默认监听 127.0.0.1，仅允许本机访问
- 不要将代理暴露在公网
- 敏感操作时注意保护个人隐私

### 9.3 数据保护

- 录制的数据包可能包含敏感信息
- 及时清空不需要的数据包记录
- 注意数据文件的安全存储

---

## 10. 扩展开发

### 10.1 添加新的拦截规则类型

1. 在 `services/traffic_rules.py` 中定义新的规则类型
2. 在 `AIInterceptorAddon` 中实现拦截逻辑
3. 在 `utcp/traffic_tools.py` 中添加工具函数
4. 更新 `utcp/tools_def.py` 中的工具定义

### 10.2 自定义数据包存储

可以修改 `services/browser_packets.py` 实现：
- 数据库存储（SQLite、MySQL）
- 分布式存储（Redis）
- 文件压缩存储

### 10.3 添加流量分析功能

可以扩展功能：
- 流量统计分析
- 威胁检测
- 自动化测试

---

## 11. 相关文件清单

| 文件路径 | 说明 |
|---------|------|
| `services/mitm_service.py` | Mitmproxy 服务核心 |
| `services/traffic_rules.py` | 流量规则管理器 |
| `services/browser_session.py` | 浏览器会话管理 |
| `services/browser_packets.py` | 数据包存储 |
| `services/recording_proxy.py` | 备选录制代理 |
| `utcp/traffic_tools.py` | UTCP 流量工具 |
| `utcp/tools_def.py` | UTCP 工具定义 |
| `routes/browser.py` | 浏览器路由 |
| `templates/recorder.html` | 记录器页面 |
| `app.py` | 应用入口 |

---

## 12. 总结

本项目的 Mitmproxy 集成实现了一个完整的 HTTP(S) 流量拦截和录制系统，具有以下特点：

1. **模块化设计**：各模块职责清晰，易于维护和扩展
2. **AI 集成**：通过 UTCP 协议让 AI 动态控制流量
3. **用户友好**：提供直观的 Web 界面
4. **功能完整**：支持流量录制、HTTPS 解密、流量修改等
5. **安全可靠**：合理的权限管理和数据保护机制

该系统适用于网络安全测试、流量分析、自动化测试等场景。
