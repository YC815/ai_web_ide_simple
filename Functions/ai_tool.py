import docker
import tempfile
import os
import sys
from io import StringIO
from typing import Optional
import tarfile
import io
import sqlite3
from .sub_agent import run_sub_agent_edit_task  # 你之後會實作的副 agent 邏輯
from .log_config import get_logger

logger = get_logger(__name__)


def get_html_code(container_name: str):
    client = docker.from_env()
    container = client.containers.get(container_name)

    result = container.exec_run("cat /usr/share/nginx/html/index.html")
    content = result.output.decode("utf-8")

    # 為每一行添加行數標記，保留所有空行
    lines = content.splitlines(keepends=True)  # 保留換行符
    numbered_lines = []

    for i, line in enumerate(lines, 1):
        # 移除末尾的換行符來顯示，但保留原始結構
        line_content = line.rstrip('\n\r')
        numbered_lines.append(f"{i:2d}: {line_content}")

    # 如果原始內容為空或只有換行符，也要顯示行號
    if not lines:
        numbered_lines.append("1: ")

    return '\n'.join(numbered_lines)


def get_js_code(container_name: str):
    client = docker.from_env()
    container = client.containers.get(container_name)

    result = container.exec_run("cat /usr/share/nginx/html/index.js")
    content = result.output.decode("utf-8")

    # 為每一行添加行數標記，保留所有空行
    lines = content.splitlines(keepends=True)  # 保留換行符
    numbered_lines = []

    for i, line in enumerate(lines, 1):
        # 移除末尾的換行符來顯示，但保留原始結構
        line_content = line.rstrip('\n\r')
        numbered_lines.append(f"{i:2d}: {line_content}")

    # 如果原始內容為空或只有換行符，也要顯示行號
    if not lines:
        numbered_lines.append("1: ")

    return '\n'.join(numbered_lines)


def get_css_code(container_name: str):
    client = docker.from_env()
    container = client.containers.get(container_name)

    result = container.exec_run("cat /usr/share/nginx/html/index.css")
    content = result.output.decode("utf-8")

    # 為每一行添加行數標記，保留所有空行
    lines = content.splitlines(keepends=True)  # 保留換行符
    numbered_lines = []

    for i, line in enumerate(lines, 1):
        # 移除末尾的換行符來顯示，但保留原始結構
        line_content = line.rstrip('\n\r')
        numbered_lines.append(f"{i:2d}: {line_content}")

    # 如果原始內容為空或只有換行符，也要顯示行號
    if not lines:
        numbered_lines.append("1: ")

    return '\n'.join(numbered_lines)


def create_tar_from_file(filepath: str, arcname: str) -> bytes:
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
        tar.add(filepath, arcname=arcname)
    tar_stream.seek(0)
    return tar_stream.read()


def get_latest_user_message(session_id: str, project_name: Optional[str] = None) -> Optional[str]:
    """
    從資料庫中取得最新的使用者訊息
    """
    # 建立專案特定的 session ID
    if project_name:
        full_session_id = f"{project_name}::{session_id}"
    else:
        full_session_id = session_id

    try:
        conn = sqlite3.connect("chat_history.db")
        c = conn.cursor()
        c.execute("""
            SELECT content FROM messages
            WHERE session_id = ? AND role = 'user'
            ORDER BY timestamp DESC
            LIMIT 1
        """, (full_session_id,))
        result = c.fetchone()
        conn.close()

        if result:
            return result[0]
        logger.warning(f"在 session '{full_session_id}' 中找不到使用者訊息")
        return None
    except Exception as e:
        logger.error(f"無法取得最新使用者訊息: {str(e)}", exc_info=True)
        return None


def edit_request(container_name: str, session_id: str, project_name: Optional[str] = None) -> str:
    """
    自動從最近的使用者輸入生成修改任務，並交由副 agent 處理
    """
    latest_input = get_latest_user_message(session_id, project_name)
    if not latest_input:
        return "[❌] 無法取得最近的使用者輸入。請確認聊天歷史存在。"

    logger.info(f"使用最新使用者輸入執行編輯任務: '{latest_input[:100]}...'")
    return run_sub_agent_edit_task(container_name, latest_input)
