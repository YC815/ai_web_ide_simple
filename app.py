from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import re
import uuid

from Functions.system import get_containers, create_container
from Functions.ai_chat import (
    chat_with_ai,
    chat_with_ai_stream,
    get_all_sessions,
    get_sessions_by_project,
    load_chat_history,
    init_chat_session,
    delete_session,
    create_project_session_id,
)
from Functions.log_config import setup_logging, get_logger

# 設定日誌模式 - 可透過變數控制
log_to_file = False
setup_logging(log_to_file=log_to_file)
logger = get_logger(__name__)


app = Flask(
    __name__,
    static_folder="web/static",
    template_folder="web/templates"
)
app.secret_key = os.urandom(24)


@app.route("/")
def home():
    containers = get_containers()
    return render_template("index.html", containers=containers)


@app.route("/project/<project_name>")
def select_project(project_name: str):
    containers = get_containers()
    container_info = next((c for c in containers if c["name"] == project_name), None)

    if not container_info:
        return redirect(url_for("home"))

    session["project_name"] = project_name
    session["project_port"] = container_info["port"]

    # 檢查該專案是否已有現有的對話 session
    existing_sessions = get_sessions_by_project(project_name)

    if existing_sessions:
        # 如果有現有對話，跳轉到最新的對話
        latest_session = existing_sessions[0]  # get_sessions_by_project 已按時間排序
        return redirect(url_for("chat_session", session_id=latest_session["session_id"]))
    else:
        # 如果沒有現有對話，創建新的對話
        new_session_id = str(uuid.uuid4())
        return redirect(url_for("chat_session", session_id=new_session_id))


@app.route("/chat")
def chat_home():
    session.pop("project_name", None)
    session.pop("project_port", None)
    new_session_id = str(uuid.uuid4())
    return redirect(url_for("chat_session", session_id=new_session_id))


@app.route("/chat/<session_id>")
def chat_session(session_id: str):
    if "project_name" not in session:
        return redirect(url_for("home"))

    project_name = session.get("project_name")

    # 初始化聊天 session，包含專案資訊
    init_chat_session(session_id, project_name)

    # 取得該專案的所有對話 session（有實際對話內容的）
    sessions = get_sessions_by_project(project_name) if project_name else []

    # 確保當前 session 出現在列表中（即使只有 system 訊息）
    current_session_in_list = any(s['session_id'] == session_id for s in sessions)
    if not current_session_in_list:
        # 如果當前 session 不在列表中，添加它
        full_session_id = create_project_session_id(session_id, project_name)
        sessions.insert(0, {
            'session_id': session_id,
            'full_session_id': full_session_id,
            'project_name': project_name,
            'last_message_time': None  # 新創建的 session
        })

    # 載入該專案的聊天歷史
    chat_history = load_chat_history(session_id, project_name)

    return render_template(
        "chat.html",
        sessions=sessions,
        current_session=session_id,
        chat_history=chat_history,
        project_name=project_name,
        project_port=session.get("project_port"),
    )


@app.route("/api/chat/<session_id>", methods=["DELETE"])
def delete_chat_session(session_id: str):
    try:
        project_name = session.get("project_name")

        # 刪除指定的 session
        delete_session(session_id, project_name)

        # 檢查該專案是否還有其他 session
        remaining_sessions = get_sessions_by_project(project_name) if project_name else []

        return jsonify({
            "success": True,
            "message": f"Session '{session_id}' deleted.",
            "remaining_sessions_count": len(remaining_sessions),
            "is_last_session": len(remaining_sessions) == 0
        })
    except Exception as e:
        logger.error(f"刪除 session 時發生錯誤: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/new_session_with_project")
def new_session_with_project():
    """創建新的對話 session 但保留專案資訊"""
    if "project_name" not in session:
        return redirect(url_for("home"))

    new_session_id = str(uuid.uuid4())
    return redirect(url_for("chat_session", session_id=new_session_id))


@app.route("/api/exit_project")
def exit_project():
    """離開專案並清除專案資訊，返回首頁"""
    session.pop("project_name", None)
    session.pop("project_port", None)
    return redirect(url_for("home"))


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    if not data or "message" not in data or "session_id" not in data:
        return jsonify({"error": "請求格式錯誤"}), 400

    user_input = data["message"]
    session_id = data["session_id"]
    project_name = session.get("project_name")

    if not project_name:
        return jsonify({"error": "未選擇專案，請返回首頁選擇"}), 400

    logger.info(f"收到聊天請求 - 專案: {project_name}, 使用者輸入: {user_input}")

    try:
        ai_response = chat_with_ai(user_input, session_id, project_name)
        logger.info(f"AI 回應內容 (長度: {len(ai_response)}): {ai_response[:200]}...")
        return jsonify({"response": ai_response})
    except Exception as e:
        logger.error(f"與 AI 對話時發生錯誤: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat_stream")
def api_chat_stream():
    """支援 Server-Sent Events 的聊天 API"""
    user_input = request.args.get("message", "")
    session_id = request.args.get("session_id", "")
    project_name = session.get("project_name")

    if not user_input or not session_id:
        return jsonify({"error": "請求參數錯誤"}), 400

    if not project_name:
        return jsonify({"error": "未選擇專案，請返回首頁選擇"}), 400

    logger.info(f"收到 streaming 聊天請求 - 專案: {project_name}, 使用者輸入: {user_input}")

    def generate():
        try:
            import json
            import time
            import queue
            import threading

            # 建立一個佇列來收集狀態訊息
            status_queue = queue.Queue()

            def status_callback(message):
                status_queue.put(message)

            # 發送初始狀態
            data = json.dumps({"type": "status", "message": "開始處理您的請求..."}, ensure_ascii=False)
            yield f"data: {data}\n\n"
            time.sleep(0.1)

            # 在另一個執行緒中執行 AI 聊天
            result_container = {"response": None, "error": None}

            def run_chat():
                try:
                    logger.info(f"開始執行 AI 聊天 - 專案: {project_name}")
                    result_container["response"] = chat_with_ai_stream(
                        user_input,
                        session_id,
                        project_name,
                        status_callback
                    )
                    logger.info(f"AI 執行完成，回應長度: {len(result_container['response'])}")
                except Exception as e:
                    logger.error(f"執行 AI 聊天時發生錯誤: {e}", exc_info=True)
                    result_container["error"] = str(e)

            chat_thread = threading.Thread(target=run_chat)
            chat_thread.start()

            # 持續檢查狀態佇列和執行緒狀態
            while chat_thread.is_alive():
                try:
                    # 檢查是否有新的狀態訊息
                    message = status_queue.get_nowait()
                    data = json.dumps({"type": "status", "message": message}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                except queue.Empty:
                    time.sleep(0.1)  # 短暫等待

            # 處理剩餘的狀態訊息
            while not status_queue.empty():
                try:
                    message = status_queue.get_nowait()
                    data = json.dumps({"type": "status", "message": message}, ensure_ascii=False)
                    yield f"data: {data}\n\n"
                except queue.Empty:
                    break

            # 發送最終回應或錯誤
            if result_container["error"]:
                error_data = json.dumps({"type": "error", "message": result_container["error"]}, ensure_ascii=False)
                yield f"data: {error_data}\n\n"
            else:
                response_data = json.dumps({"type": "response", "message": result_container["response"]}, ensure_ascii=False)
                yield f"data: {response_data}\n\n"

        except Exception as e:
            logger.error(f"Stream 聊天時發生錯誤: {e}", exc_info=True)
            error_data = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return app.response_class(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
        }
    )


@app.route("/create", methods=["POST"])
def create_project():
    try:
        data = request.get_json()
        if not data or 'project_name' not in data:
            return jsonify({"error": "請求格式錯誤，缺少 'project_name'"}), 400

        project_name = data.get("project_name")

        if not project_name:
            return jsonify({"error": "專案名稱不可為空"}), 400

        if not re.match(r'^[a-zA-Z0-9_-]+$', project_name):
            return jsonify({"error": "專案名稱格式不正確，只能包含英文字母、數字、底線與連字號。"}), 400

        logger.info(f"收到建立專案請求: {project_name}")
        container = create_container(container_name=project_name)
        return jsonify({"success": True, "container_id": container.id, "message": f"容器 '{container.name}' 建立成功！"}), 201

    except Exception as e:
        logger.error(f"建立容器時發生錯誤: {e}", exc_info=True)
        return jsonify({"error": f"伺服器內部錯誤: {e}"}), 500


@app.route("/api/container/start", methods=["POST"])
def start_container_route():
    data = request.get_json()
    container_name = data.get("container_name")
    if not container_name:
        return jsonify({"success": False, "error": "Missing container name"}), 400
    try:
        from Functions.system import start_container
        start_container(container_name)
        return jsonify({"success": True, "message": f"Container {container_name} started."})
    except Exception as e:
        logger.error(f"啟動容器 {container_name} 時發生錯誤: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/container/stop", methods=["POST"])
def stop_container_route():
    data = request.get_json()
    container_name = data.get("container_name")
    if not container_name:
        return jsonify({"success": False, "error": "Missing container name"}), 400
    try:
        from Functions.system import stop_container
        stop_container(container_name)
        return jsonify({"success": True, "message": f"Container {container_name} stopped."})
    except Exception as e:
        logger.error(f"停止容器 {container_name} 時發生錯誤: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/container/delete", methods=["POST"])
def delete_container_route():
    data = request.get_json()
    container_name = data.get("container_name")
    if not container_name:
        return jsonify({"success": False, "error": "Missing container name"}), 400
    try:
        from Functions.system import delete_container
        delete_container(container_name)
        return jsonify({"success": True, "message": f"Container {container_name} deleted successfully."})
    except Exception as e:
        logger.error(f"刪除容器 {container_name} 時發生錯誤: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001)
