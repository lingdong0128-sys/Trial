# UTCP 工具开发说明

本文档说明在本项目中如何添加与编写 UTCP 工具，以及 UTCP 与 MCP 在形态上的区别。

## UTCP 与 MCP 的形态区别

| 维度 | UTCP（本项目中） | MCP |
|------|------------------|-----|
| **形态** | **静态** | **动态** |
| **存在方式** | 工具是应用代码的一部分，随 Flask 应用一起启动，以 HTTP 路由形式暴露 | 工具由独立 MCP 服务提供，需预先启动该服务，客户端通过协议发现并调用 |
| **注册时机** | 应用启动时由 Blueprint/路由注册确定，工具集固定 | 连接 MCP 服务时动态发现工具列表，可随服务配置变化 |
| **部署** | 与 Web 应用同一进程，无需额外进程 | 通常为独立进程（或远程服务），需要单独启动与维护 |

因此：**UTCP 工具在本项目中是“静态”的**——工具列表和实现都写在代码里，随应用部署即生效；**MCP 工具是“动态”的**——以服务形式存在，需要先启动服务，再通过协议发现和调用。

---

## 代码结构（utcp 包）

UTCP 相关代码位于项目根目录下的 **`utcp/`** 包中，按功能拆分为独立文件：

| 文件 | 职责 |
|------|------|
| `utcp/__init__.py` | 导出 `utcp_bp`，并导入各子模块以完成路由注册 |
| `utcp/blueprint.py` | 定义统一 Blueprint `utcp_bp` |
| `utcp/health.py` | 健康检查端点 `GET /api/utcp/health` |
| `utcp/datetime_tool.py` | 日期时间工具：`get_datetime()` 与 `GET/POST /api/utcp/datetime` |

应用在 `app.py` 中通过 `from routes import utcp_bp` 取得 Blueprint（`routes` 从 `utcp` 包再导出），并挂载到 `/api/utcp`。

---

## 如何添加新的 UTCP 工具

### 方式一：在 utcp 包中新增功能模块（推荐）

1. **在 `utcp/` 下新建模块**，例如 `utcp/your_tool.py`，实现业务函数与路由：

   ```python
   from flask import request, jsonify
   from .blueprint import utcp_bp

   def your_tool_name(param1: str = None, param2: str = None, **kwargs) -> dict:
       """工具说明。"""
       return {
           "success": True,
           "protocol": "UTCP",
           "message": "ok",
           "data": { ... },
       }

   @utcp_bp.route("/your-tool-path", methods=["GET", "POST"])
   def utcp_your_tool():
       if request.method == "GET":
           param1 = request.args.get("param1")
           param2 = request.args.get("param2")
       else:
           data = request.get_json() or request.form or {}
           data = data if isinstance(data, dict) else {}
           param1 = data.get("param1")
           param2 = data.get("param2")
       result = your_tool_name(param1=param1, param2=param2)
       return jsonify(result)
   ```

2. **在 `utcp/__init__.py` 中导入新模块**，以完成路由注册：

   ```python
   from . import your_tool  # noqa: F401
   ```

3. 新端点将自动挂载为 `GET/POST /api/utcp/your-tool-path`，无需改 `app.py`。

### 方式二：多个 Blueprint 或子路径

若需独立前缀或单独 Blueprint，可在 `utcp/` 内再建子包或新 Blueprint，并在 `app.py` 中注册到 `/api/utcp/...` 等路径。

---

## 工具应如何编写

### 1. 函数形态（工具逻辑）

- **位置**：放在 `utcp/` 包下对应功能模块中（如 `utcp/datetime_tool.py`、`utcp/your_tool.py`）。
- **签名**：参数建议使用关键字参数 + `**kwargs`，便于从 GET 查询串或 POST body 里统一取参。
- **返回值**：统一返回 `dict`，便于在路由里 `jsonify(result)` 返回 JSON。

推荐结构：

```python
def tool_xxx(arg1: str = None, arg2: str = None, **kwargs) -> dict:
    """
    一句话说明工具用途。
    参数：
        arg1: 说明
        arg2: 说明
    返回：
        含 success / protocol / message / data 的 dict
    """
    return {
        "success": True,
        "protocol": "UTCP",
        "message": "可选",
        "data": { ... },
    }
```

- `success`: 布尔，表示本次调用是否成功。
- `protocol`: 固定 `"UTCP"` 便于客户端识别。
- `message`: 可选，错误或说明信息。
- `data`: 业务数据，结构由该工具自行约定。

### 2. 路由形态（HTTP 暴露）

- **路径**：使用小写、短横线，如 `/query`、`/your-tool-path`。
- **方法**：与现有占位一致，支持 `GET` 和 `POST` 即可；GET 用 `request.args`，POST 用 `request.get_json()` 或 `request.form`。
- **响应**：始终 `return jsonify(result)`，保证 Content-Type 为 JSON。

示例（与现有 `utcp_query` 一致风格）：

```python
@utcp_bp.route("/your-tool-path", methods=["GET", "POST"])
def utcp_your_tool():
    """UTCP 工具：简短描述"""
    if request.method == "GET":
        arg1 = request.args.get("arg1")
        arg2 = request.args.get("arg2")
    else:
        data = request.get_json() or request.form or {}
        data = data if isinstance(data, dict) else {}
        arg1 = data.get("arg1")
        arg2 = data.get("arg2")
    result = tool_xxx(arg1=arg1, arg2=arg2)
    return jsonify(result)
```

### 3. 错误与边界

- 参数缺失或非法时，在业务函数内设置 `success: False`，并在 `message` 中说明原因。
- 避免在路由层抛未捕获异常，尽量在工具函数内返回错误结构，保证客户端始终拿到 JSON。

---

## 现有 UTCP 端点一览

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/utcp/health` | GET | 健康检查 |
| `/api/utcp/datetime` | GET / POST | 获取当前日期时间及时区、星期、时间戳等，可选 `timezone_hours`（如 8 表示 UTC+8） |

Web 端提供 **UTCP 控制台** 页面（导航栏「UTCP 控制台」或访问 `/utcp`），可对上述接口进行调用并查看 JSON 响应。

新工具按上述规范添加后，将自动挂载在 `/api/utcp/...` 下，与现有端点风格一致。

---

## 小结

- **UTCP 工具在本项目中是静态的**：随 Flask 应用一起启动，以 HTTP 路由形式提供，无需单独服务进程。
- **代码位置**：UTCP 逻辑在 **`utcp/`** 包下，按功能拆分为 `blueprint.py`、`health.py`、`datetime_tool.py` 等，新工具可新增独立模块并在 `__init__.py` 中导入注册。
- **编写规范**：业务函数返回统一结构的 `dict`（含 `success`/`protocol`/`message`/`data`），路由负责从请求中取参并 `jsonify` 返回。
