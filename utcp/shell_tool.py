# -*- coding: utf-8 -*-
"""UTCP 工具：在 Linux 上执行 shell 命令。仅考虑 Linux 兼容性。"""
import subprocess
import threading
import time

from flask import request, jsonify
from .blueprint import utcp_bp


CHECK_INTERVAL = 60
HARD_LIMIT = 300


def run_shell(
    command: str,
    timeout_seconds: int = 1800,
    cwd: str = None,
    llm_judge_callback=None,
    **kwargs
) -> dict:
    """
    在服务器上执行 shell 命令（Linux）。
    参数：
        command: 要执行的命令字符串。
        timeout_seconds: 当未提供 llm_judge_callback 时使用的超时秒数，默认 1800，最大 14400。
        cwd: 可选，工作目录路径。
        llm_judge_callback: 可选，(command, stdout, stderr) -> bool，返回 True 表示判定为卡住应中止。
            若提供，则采用「每 1 分钟检查 + AI 判断是否继续」，总时长上限 5 分钟。
    返回：
        含 success、stdout、stderr、returncode、message 的 dict。
    """
    if not command or not str(command).strip():
        return {
            "success": False,
            "protocol": "UTCP",
            "message": "command 不能为空",
            "data": None,
        }

    if llm_judge_callback is not None:
        return _run_shell_with_judge(command, cwd=cwd, judge_callback=llm_judge_callback)

    try:
        timeout = max(1, min(14400, int(timeout_seconds))) if timeout_seconds is not None else 1800
    except (TypeError, ValueError):
        timeout = 1800
    try:
        proc = subprocess.run(
            ["/bin/sh", "-c", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or None,
        )
        return {
            "success": True,
            "protocol": "UTCP",
            "message": "ok",
            "data": {
                "stdout": proc.stdout or "",
                "stderr": proc.stderr or "",
                "returncode": proc.returncode,
            },
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "protocol": "UTCP",
            "message": f"命令执行超时（{timeout} 秒）",
            "data": None,
        }
    except Exception as e:
        return {
            "success": False,
            "protocol": "UTCP",
            "message": str(e),
            "data": None,
        }


def _run_shell_with_judge(command: str, cwd: str = None, judge_callback=None) -> dict:
    """
    使用 Popen + 每 1 分钟检查输出，调用 judge_callback 判断是否卡住；
    总时长上限 5 分钟（CHECK_INTERVAL=60，HARD_LIMIT=300）。
    """
    stdout_buf = []
    stderr_buf = []
    buf_lock = threading.Lock()

    def read_stream(stream, buf):
        try:
            for line in iter(stream.readline, ""):
                with buf_lock:
                    buf.append(line)
        except Exception:
            pass
        try:
            stream.close()
        except Exception:
            pass

    try:
        proc = subprocess.Popen(
            ["/bin/sh", "-c", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd or None,
        )
    except Exception as e:
        return {
            "success": False,
            "protocol": "UTCP",
            "message": str(e),
            "data": None,
        }

    t_out = threading.Thread(target=read_stream, args=(proc.stdout, stdout_buf))
    t_err = threading.Thread(target=read_stream, args=(proc.stderr, stderr_buf))
    t_out.daemon = True
    t_err.daemon = True
    t_out.start()
    t_err.start()

    start = time.monotonic()
    last_check = start
    while True:
        now = time.monotonic()
        elapsed = now - start
        if elapsed >= HARD_LIMIT:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            with buf_lock:
                so = "".join(stdout_buf)
                se = "".join(stderr_buf)
            return {
                "success": False,
                "protocol": "UTCP",
                "message": f"命令执行已达上限（{HARD_LIMIT} 秒）",
                "data": {"stdout": so, "stderr": se, "returncode": None},
            }

        if proc.poll() is not None:
            t_out.join(timeout=1)
            t_err.join(timeout=1)
            with buf_lock:
                so = "".join(stdout_buf)
                se = "".join(stderr_buf)
            return {
                "success": True,
                "protocol": "UTCP",
                "message": "ok",
                "data": {
                    "stdout": so,
                    "stderr": se,
                    "returncode": proc.returncode,
                },
            }

        if now - last_check >= CHECK_INTERVAL and judge_callback:
            with buf_lock:
                so = "".join(stdout_buf)
                se = "".join(stderr_buf)
            if judge_callback(command, so, se):
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                return {
                    "success": False,
                    "protocol": "UTCP",
                    "message": "命令被判定为可能卡住而中止",
                    "data": {"stdout": so, "stderr": se, "returncode": None},
                }
            last_check = now

        time.sleep(2)


@utcp_bp.route("/shell", methods=["POST"])
def utcp_shell():
    """UTCP 工具：执行 shell 命令。POST body: command, timeout_seconds?, cwd?"""
    data = request.get_json() or {}
    data = data if isinstance(data, dict) else {}
    result = run_shell(
        command=data.get("command") or "",
        timeout_seconds=data.get("timeout_seconds"),
        cwd=data.get("cwd"),
    )
    return jsonify(result)
