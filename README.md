# Trial Web 应用

基于 Python (Flask) 的 Web 应用，支持多模型对话、后台 API 配置与 UTCP 占位接口。

## 功能

- **全局登录**：默认账号 `root` / 密码 `itzx`
- **对话页**：选择 QWEN 或 DeepSeek 模型进行对话，预留后续模型扩展
- **后台配置**：在「后台配置」页配置 QWEN、DeepSeek 的 API Base、API Key、模型名
- **UTCP 占位**：`/api/utcp/query`、`/api/utcp/health` 为 UTCP 协议预留端口，内含 `query_application()` 占位方法便于后续接入

## 环境

- Python 3.11（已用 conda 在项目下创建环境）

激活环境：

```bash
conda activate Trial
```

若希望使用名为 `Trial` 的 conda 环境且具备 conda envs 目录写权限，可执行：

```bash
conda create -n Trial python=3.11 -y
conda activate Trial
```

## 安装与运行

```bash
conda activate Trial
pip install -r requirements.txt
python app.py
```

访问：<http://127.0.0.1:5000>，使用 `root` / `itzx` 登录。

## 接口说明

| 说明           | 路径/方法        |
|----------------|------------------|
| 登录           | GET/POST `/auth/login` |
| 对话页         | GET `/`          |
| 对话 API       | POST `/api/chat`，body: `{ "model": "qwen|deepseek", "messages": [...] }` |
| 模型列表       | GET `/api/models` |
| 后台配置页     | GET `/admin/`    |
| 保存配置       | POST `/admin/api/config` |
| UTCP 查询占位  | GET/POST `/api/utcp/query`，可选 `app_id` |
| UTCP 健康占位  | GET `/api/utcp/health` |

## 配置存储

API 配置保存在项目根目录下的 `config.json`，按需备份或迁移。
