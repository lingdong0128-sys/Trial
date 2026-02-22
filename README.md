# Trial Web 应用

基于 Python (Flask) 的 Web 应用，支持多模型对话、后台 API 配置、UTCP 协议接口与知识库检索。

## 功能

- **全局登录**：默认账号 `root` / 密码 `itzx`
- **对话页**：选择阿里云百炼或 DeepSeek 等模型，支持流式回复；可选启用自动化工作流（UTCP 工具：执行命令、读写文件、知识库检索等）
- **设置**：全局配置（API 检测、UTCP 开关、安全模式、AI 默认语言、前置提示词）、API 信息、知识库状态、UTCP 控制台、关于我们
- **知识库**：项目下 `knowledge/` 目录中的 `.md`、`.txt` 可被 AI 通过 `search_knowledge` 工具按需检索，适用于 CTF、漏洞利用等场景
- **安全模式**：开启后禁止 AI 修改项目自身文件（仅允许写入上传目录）
- **UTCP 接口**：`utcp/` 包提供健康检查、日期时间、Shell、文件读写等；Web 端有「UTCP 控制台」可调用并查看响应

## 环境

- Python 3.11（建议使用 conda 在项目下创建环境）

激活环境：

```bash
conda activate Trial
```

若需创建名为 `Trial` 的 conda 环境：

```bash
conda create -n Trial python=3.11 -y
conda activate Trial
```

## 安装与运行

```bash
# Conda环境
conda activate Trial
pip install -r requirements.txt
# VNC环境
apt update
apt install -y xvfb x11vnc websockify fluxbox tigervnc-standalone-server
#mimproxy环境
apt install mitmproxy
# 运行
python app.py
```

访问：<http://127.0.0.1:5000>，使用 `root` / `itzx` 登录。
代理：服务器:8888
## 接口说明

| 说明           | 路径/方法        |
|----------------|------------------|
| 登录           | GET/POST `/auth/login` |
| 对话页         | GET `/`          |
| 流式对话       | POST `/api/chat/stream`，body: `provider_id`, `model`, `messages`, `use_utcp_tools` 等 |
| 模型与配置     | GET `/api/models` |
| 设置-全局配置  | GET `/settings/global` |
| 设置-知识库    | GET `/settings/knowledge` |
| UTCP 健康检查  | GET `/api/utcp/health` |
| UTCP 控制台页  | GET `/utcp`（重定向至设置下 UTCP 控制台） |

## 配置存储

API 与全局配置保存在项目根目录下的 `config.json`；对话历史在 `data/conversations.json`。知识库内容位于 `knowledge/` 目录，可按需添加 `.md` / `.txt` 供 AI 检索。
