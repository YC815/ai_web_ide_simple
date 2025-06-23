import docker
import tempfile
import os
import sys
from io import StringIO

import tarfile
import io


def get_html_code(container_name: str):
    client = docker.from_env()
    container = client.containers.get(container_name)

    result = container.exec_run("cat /usr/share/nginx/html/index.html")
    return result.output.decode("utf-8")


def get_js_code(container_name: str):
    client = docker.from_env()
    container = client.containers.get(container_name)

    result = container.exec_run("cat /usr/share/nginx/html/index.js")
    return result.output.decode("utf-8")


def get_css_code(container_name: str):
    client = docker.from_env()
    container = client.containers.get(container_name)

    result = container.exec_run("cat /usr/share/nginx/html/index.css")
    return result.output.decode("utf-8")


def create_tar_from_file(filepath: str, arcname: str) -> bytes:
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode='w') as tar:
        tar.add(filepath, arcname=arcname)
    tar_stream.seek(0)
    return tar_stream.read()


def diff_code(container_name: str, diff_code: str, language: str) -> str:
    """
    套用 diff patch 到 Docker 容器中的檔案

    Args:
        container_name: Docker 容器名稱
        diff_code: diff patch 內容
        language: 語言類型 (html, js, css)

    Returns:
        str: 執行結果訊息
    """
    # 建立日誌捕獲
    log_capture = StringIO()

    def log_print(message):
        print(message)  # 保持原有的 print 功能
        log_capture.write(message + '\n')

    log_print(f"[DEBUG] 開始處理 diff，容器: {container_name}, 語言: {language}")
    log_print(f"[DEBUG] Diff 內容長度: {len(diff_code)} 字元")

    try:
        # 初始化 Docker 客戶端
        client = docker.from_env()
        log_print("[DEBUG] Docker 客戶端初始化成功")

        # 獲取容器
        container = client.containers.get(container_name)
        log_print(f"[DEBUG] 成功獲取容器: {container.name}")

        # 檢查容器狀態
        container.reload()
        if container.status != 'running':
            error_msg = f"[❌ 容器錯誤] 容器 {container_name} 狀態為 {container.status}，需要運行中狀態"
            log_print(error_msg)
            return f"{error_msg}\n\n[除錯日誌]\n{log_capture.getvalue()}"

    except docker.errors.NotFound:
        error_msg = f"[❌ 容器錯誤] 找不到容器: {container_name}"
        log_print(error_msg)
        return f"{error_msg}\n\n[除錯日誌]\n{log_capture.getvalue()}"
    except docker.errors.APIError as e:
        error_msg = f"[❌ Docker API 錯誤] {str(e)}"
        log_print(error_msg)
        return f"{error_msg}\n\n[除錯日誌]\n{log_capture.getvalue()}"
    except Exception as e:
        error_msg = f"[❌ Docker 連接錯誤] {str(e)}"
        log_print(error_msg)
        return f"{error_msg}\n\n[除錯日誌]\n{log_capture.getvalue()}"

    # 創建臨時檔案
    try:
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix=".diff", encoding='utf-8') as tmp:
            tmp.write(diff_code)
            diff_path = tmp.name
        log_print(f"[DEBUG] 臨時 diff 檔案創建於: {diff_path}")

        # 驗證檔案內容
        with open(diff_path, 'r', encoding='utf-8') as f:
            written_content = f.read()
            log_print(f"[DEBUG] 寫入檔案的內容長度: {len(written_content)} 字元")
            if len(written_content) != len(diff_code):
                log_print("[WARNING] 寫入的內容長度與原始內容不符")

    except Exception as e:
        error_msg = f"[❌ 檔案操作錯誤] 無法創建臨時檔案: {str(e)}"
        log_print(error_msg)
        return f"{error_msg}\n\n[除錯日誌]\n{log_capture.getvalue()}"

    try:
        # 上傳 patch.diff 到容器的 /tmp 位置
        log_print("[DEBUG] 開始上傳 patch 檔案到容器...")
        tar_data = create_tar_from_file(diff_path, "patch.diff")
        container.put_archive(path="/tmp", data=tar_data)
        log_print("[DEBUG] Patch 檔案上傳成功")

        # 驗證檔案是否成功上傳
        verify_cmd = "ls -la /tmp/patch.diff"
        verify_result = container.exec_run(verify_cmd)
        if verify_result.exit_code == 0:
            log_print(f"[DEBUG] 檔案驗證成功: {verify_result.output.decode('utf-8').strip()}")
        else:
            error_msg = f"[❌ 檔案上傳驗證失敗] {verify_result.output.decode('utf-8').strip()}"
            log_print(error_msg)
            return f"{error_msg}\n\n[除錯日誌]\n{log_capture.getvalue()}"

        # 根據語言類型確定目標文件路徑
        target_dir = "/usr/share/nginx/html"

        # 映射語言類型到文件名
        file_mapping = {
            'html': 'index.html',
            'css': 'index.css',
            'js': 'index.js',
            'javascript': 'index.js'
        }

        target_file = file_mapping.get(language.lower())
        if not target_file:
            error_msg = f"[❌ 語言類型錯誤] 不支援的語言類型: {language}，支援的類型: html, css, js"
            log_print(error_msg)
            return f"{error_msg}\n\n[除錯日誌]\n{log_capture.getvalue()}"

        target_file_path = f"{target_dir}/{target_file}"

        # 檢查目標文件是否存在
        file_check_cmd = f"ls -la {target_file_path}"
        file_result = container.exec_run(file_check_cmd)
        if file_result.exit_code != 0:
            error_msg = f"[❌ 文件錯誤] 目標文件不存在: {target_file_path}\n{file_result.output.decode('utf-8').strip()}"
            log_print(error_msg)
            return f"{error_msg}\n\n[除錯日誌]\n{log_capture.getvalue()}"
        else:
            log_print(f"[DEBUG] 目標文件確認存在: {target_file_path}")
            log_print(f"[DEBUG] 文件資訊:\n{file_result.output.decode('utf-8').strip()}")

        # Dry-run 模擬是否能成功套用
        log_print("[DEBUG] 開始執行 dry-run 測試...")
        dry_run_cmd = f"sh -c 'cd {target_dir} && patch --dry-run --batch --forward -p0 < /tmp/patch.diff'"
        log_print(f"[DEBUG] Dry-run 命令: {dry_run_cmd}")

        dry_run_result = container.exec_run(dry_run_cmd)
        log_print(f"[DEBUG] Dry-run 結果 - 退出碼: {dry_run_result.exit_code}")
        log_print(f"[DEBUG] Dry-run 輸出: {dry_run_result.output.decode('utf-8').strip()}")

        if dry_run_result.exit_code != 0:
            error_msg = f"[❌ PATCH DRY-RUN 失敗]\n退出碼: {dry_run_result.exit_code}\n輸出: {dry_run_result.output.decode('utf-8').strip()}"
            log_print(error_msg)

            # 顯示 patch 檔案內容以便調試
            patch_content_cmd = "cat /tmp/patch.diff"
            patch_result = container.exec_run(patch_content_cmd)
            if patch_result.exit_code == 0:
                log_print(f"[DEBUG] Patch 檔案內容:\n{patch_result.output.decode('utf-8')}")

            return f"{error_msg}\n\n[除錯日誌]\n{log_capture.getvalue()}"

        # 實際執行 patch
        log_print("[DEBUG] Dry-run 成功，開始實際套用 patch...")
        apply_cmd = f"sh -c 'cd {target_dir} && patch --batch --forward -p0 < /tmp/patch.diff'"
        log_print(f"[DEBUG] Apply 命令: {apply_cmd}")

        apply_result = container.exec_run(apply_cmd)
        log_print(f"[DEBUG] Apply 結果 - 退出碼: {apply_result.exit_code}")
        log_print(f"[DEBUG] Apply 輸出: {apply_result.output.decode('utf-8').strip()}")

        if apply_result.exit_code == 0:
            success_msg = f"[✅ PATCH 套用成功]\n{apply_result.output.decode('utf-8').strip()}"
            log_print(success_msg)
            return f"{success_msg}\n\n[除錯日誌]\n{log_capture.getvalue()}"
        else:
            error_msg = f"[❌ PATCH 套用失敗]\n退出碼: {apply_result.exit_code}\n輸出: {apply_result.output.decode('utf-8').strip()}"
            log_print(error_msg)
            return f"{error_msg}\n\n[除錯日誌]\n{log_capture.getvalue()}"

    except docker.errors.APIError as e:
        error_msg = f"[❌ Docker API 錯誤] 執行容器命令時發生錯誤: {str(e)}"
        log_print(error_msg)
        return f"{error_msg}\n\n[除錯日誌]\n{log_capture.getvalue()}"
    except Exception as e:
        error_msg = f"[❌ 未預期錯誤] {str(e)}"
        log_print(error_msg)
        return f"{error_msg}\n\n[除錯日誌]\n{log_capture.getvalue()}"
    finally:
        # 清理臨時檔案
        try:
            if os.path.exists(diff_path):
                os.remove(diff_path)
                log_print(f"[DEBUG] 臨時檔案已清理: {diff_path}")
        except Exception as e:
            log_print(f"[WARNING] 清理臨時檔案失敗: {str(e)}")
