# -*- coding: utf-8 -*-
"""UTCP 工具：文件读写与目录列表。仅考虑 Linux 兼容性。"""
from pathlib import Path

from flask import request, jsonify
from .blueprint import utcp_bp


def read_file(path: str, encoding: str = "utf-8", max_bytes: int = 512 * 1024, **kwargs) -> dict:
    """
    读取文件内容（Linux 路径）。
    参数：
        path: 文件路径（相对项目根或绝对路径；绝对路径需在项目根下或允许的根内）。
        encoding: 编码，默认 utf-8；若解码失败可尝试传入其他编码。
        max_bytes: 最大读取字节数，默认 512KB。
    返回：
        含 success、content、encoding、error 的 dict。
    """
    if not path or not str(path).strip():
        return {
            "success": False,
            "protocol": "UTCP",
            "message": "path 不能为空",
            "data": None,
        }
    try:
        limit = max(1, min(2 * 1024 * 1024, int(max_bytes))) if max_bytes is not None else 512 * 1024
    except (TypeError, ValueError):
        limit = 512 * 1024
    root = Path(__file__).resolve().parent.parent
    p = Path(path.strip()).resolve() if path.strip().startswith("/") else (root / path.strip()).resolve()
    try:
        p.resolve().relative_to(root)
    except ValueError:
        return {
            "success": False,
            "protocol": "UTCP",
            "message": "路径不允许访问（必须在项目根下）",
            "data": None,
        }
    if not p.exists():
        return {
            "success": False,
            "protocol": "UTCP",
            "message": "文件不存在",
            "data": None,
        }
    if not p.is_file():
        return {
            "success": False,
            "protocol": "UTCP",
            "message": "路径不是文件",
            "data": None,
        }
    try:
        raw = p.read_bytes()
        truncated = len(raw) > limit
        if truncated:
            raw = raw[:limit]
        content = raw.decode(encoding or "utf-8", errors="replace")
        return {
            "success": True,
            "protocol": "UTCP",
            "message": "ok",
            "data": {"content": content, "encoding": encoding or "utf-8", "truncated": truncated},
        }
    except Exception as e:
        return {
            "success": False,
            "protocol": "UTCP",
            "message": str(e),
            "data": None,
        }


def write_file(path: str, content: str, encoding: str = "utf-8", append: bool = False, **kwargs) -> dict:
    """
    写入文件（Linux 路径）。若目录不存在会尝试创建。
    参数：
        path: 文件路径。
        content: 要写入的内容。
        encoding: 编码。
        append: 是否追加。
    返回：
        含 success、written_path、error 的 dict。
    """
    if path is None or not str(path).strip():
        return {
            "success": False,
            "protocol": "UTCP",
            "message": "path 不能为空",
            "data": None,
        }
    root = Path(__file__).resolve().parent.parent
    p = Path(path.strip()).resolve() if path.strip().startswith("/") else (root / path.strip()).resolve()
    try:
        p.resolve().relative_to(root)
    except ValueError:
        return {
            "success": False,
            "protocol": "UTCP",
            "message": "路径不允许写入（必须在项目根下）",
            "data": None,
        }
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content or "", encoding=encoding or "utf-8", errors="replace")
        return {
            "success": True,
            "protocol": "UTCP",
            "message": "ok",
            "data": {"written_path": str(p)},
        }
    except Exception as e:
        return {
            "success": False,
            "protocol": "UTCP",
            "message": str(e),
            "data": None,
        }


def list_dir(path: str = ".", include_hidden: bool = False, **kwargs) -> dict:
    """
    列出目录下的文件和子目录（Linux 路径）。
    参数：
        path: 目录路径，默认当前目录（项目根）。
        include_hidden: 是否包含以 . 开头的条目。
    返回：
        含 success、entries（name, is_dir, size）、error 的 dict。
    """
    root = Path(__file__).resolve().parent.parent
    p = Path(path.strip()).resolve() if path and path.strip().startswith("/") else (root / (path or ".").strip()).resolve()
    try:
        p.relative_to(root)
    except ValueError:
        return {
            "success": False,
            "protocol": "UTCP",
            "message": "路径不允许访问（必须在项目根下）",
            "data": None,
        }
    if not p.exists():
        return {
            "success": False,
            "protocol": "UTCP",
            "message": "路径不存在",
            "data": None,
        }
    if not p.is_dir():
        return {
            "success": False,
            "protocol": "UTCP",
            "message": "路径不是目录",
            "data": None,
        }
    entries = []
    for e in sorted(p.iterdir()):
        if not include_hidden and e.name.startswith("."):
            continue
        try:
            entries.append({
                "name": e.name,
                "is_dir": e.is_dir(),
                "size": e.stat().st_size if e.is_file() else None,
            })
        except OSError:
            continue
    return {
        "success": True,
        "protocol": "UTCP",
        "message": "ok",
        "data": {"path": str(p), "entries": entries},
    }


def _get_request_params():
    """从 GET 或 POST 取参。"""
    if request.method == "GET":
        return request.args
    data = request.get_json() or request.form or {}
    return data if isinstance(data, dict) else {}


@utcp_bp.route("/read-file", methods=["GET", "POST"])
def utcp_read_file():
    """UTCP 工具：读取文件。参数 path, encoding?, max_bytes?"""
    p = _get_request_params()
    result = read_file(
        path=p.get("path") or "",
        encoding=p.get("encoding"),
        max_bytes=p.get("max_bytes"),
    )
    return jsonify(result)


@utcp_bp.route("/write-file", methods=["POST"])
def utcp_write_file():
    """UTCP 工具：写入文件。body: path, content, encoding?, append?"""
    data = request.get_json() or request.form or {}
    data = data if isinstance(data, dict) else {}
    result = write_file(
        path=data.get("path") or "",
        content=data.get("content"),
        encoding=data.get("encoding"),
        append=data.get("append") in (True, "true", "1"),
    )
    return jsonify(result)


@utcp_bp.route("/list-dir", methods=["GET", "POST"])
def utcp_list_dir():
    """UTCP 工具：列出目录。参数 path?, include_hidden?"""
    p = _get_request_params()
    result = list_dir(
        path=p.get("path") or ".",
        include_hidden=p.get("include_hidden") in (True, "true", "1"),
    )
    return jsonify(result)
