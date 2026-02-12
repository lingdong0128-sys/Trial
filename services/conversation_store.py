# -*- coding: utf-8 -*-
"""对话历史持久化存储"""
import json
import uuid
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONVERSATIONS_FILE = DATA_DIR / "conversations.json"


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_all():
    _ensure_data_dir()
    if not CONVERSATIONS_FILE.exists():
        return []
    with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_all(conversations):
    _ensure_data_dir()
    with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)


def list_conversations():
    """按更新时间倒序返回对话列表"""
    items = _load_all()
    items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return [{"id": c["id"], "title": c.get("title", "新对话"), "updated_at": c.get("updated_at")} for c in items]


def get_conversation(cid):
    """获取单条对话（含完整 messages）"""
    for c in _load_all():
        if c.get("id") == cid:
            return c
    return None


def create_conversation(title="新对话", messages=None):
    """创建新对话，返回完整对象"""
    conversations = _load_all()
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    conv = {
        "id": str(uuid.uuid4()),
        "title": title or "新对话",
        "messages": list(messages or []),
        "created_at": now,
        "updated_at": now,
    }
    conversations.append(conv)
    _save_all(conversations)
    return conv


def update_conversation(cid, title=None, messages=None):
    """更新对话的 title 和/或 messages"""
    conversations = _load_all()
    for c in conversations:
        if c.get("id") == cid:
            if title is not None:
                c["title"] = title
            if messages is not None:
                c["messages"] = list(messages)
            c["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            _save_all(conversations)
            return c
    return None


def delete_conversation(cid):
    """删除一条对话"""
    conversations = [c for c in _load_all() if c.get("id") != cid]
    _save_all(conversations)
    return True
