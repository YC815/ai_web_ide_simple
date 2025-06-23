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


def diagnose_patch_failure(container, target_file_path, diff_code, log_print):
    """診斷 patch 失敗的原因並提供詳細資訊"""
    try:
        # 獲取實際文件內容
        actual_result = container.exec_run(f"cat {target_file_path}")
        if actual_result.exit_code != 0:
            log_print(f"[DIAGNOSE] 無法讀取目標文件: {actual_result.output.decode('utf-8')}")
            return

        actual_content = actual_result.output.decode('utf-8')
        actual_lines = actual_content.splitlines()

        log_print(f"[DIAGNOSE] 實際文件內容 ({len(actual_lines)} 行):")
        for i, line in enumerate(actual_lines, 1):
            log_print(f"[DIAGNOSE] {i:2d}: {repr(line)}")

        # 分析 diff 內容
        log_print(f"[DIAGNOSE] Diff 內容分析:")
        diff_lines = diff_code.split('\n')
        for i, line in enumerate(diff_lines):
            if line.startswith('@@'):
                log_print(f"[DIAGNOSE] Hunk 標頭: {line}")
            elif line.startswith('-') and not line.startswith('---'):
                log_print(f"[DIAGNOSE] 要移除的行: {repr(line[1:])}")
            elif line.startswith('+') and not line.startswith('+++'):
                log_print(f"[DIAGNOSE] 要新增的行: {repr(line[1:])}")

        # 檢查檔案行數是否匹配
        log_print(f"[DIAGNOSE] 文件統計: 實際行數 {len(actual_lines)}")

    except Exception as e:
        log_print(f"[DIAGNOSE] 診斷過程發生錯誤: {str(e)}")


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

                # 執行詳細診斷
            log_print("[DEBUG] 開始執行詳細診斷...")
            diagnose_patch_failure(container, target_file_path, diff_code, log_print)

            # 向AI提供清晰的錯誤訊息和修正建議
            suggestion_msg = f"""
[💡 修正建議]
1. 請檢查diff中的行號是否與實際文件匹配
2. 請確認要修改的文字內容是否存在於文件中
3. 建議重新獲取文件內容後再生成新的diff
4. 如果是簡單的文字替換，請使用更精確的行號定位

[📋 建議步驟]
1. 先使用 get_{language}_code() 獲取最新文件內容
2. 確認要修改的具體行號和內容
3. 重新生成正確的diff patch
"""
            log_print(suggestion_msg)

            return f"{error_msg}\n{suggestion_msg}\n\n[除錯日誌]\n{log_capture.getvalue()}"

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

            # 自動獲取最新代碼狀態
            log_print("[DEBUG] 開始獲取最新代碼狀態...")
            try:
                # 根據語言類型調用對應的get函數
                language_lower = language.lower()
                if language_lower == 'html':
                    latest_code = get_html_code(container_name)
                    log_print("[DEBUG] 成功獲取最新 HTML 代碼")
                elif language_lower in ['css']:
                    latest_code = get_css_code(container_name)
                    log_print("[DEBUG] 成功獲取最新 CSS 代碼")
                elif language_lower in ['js', 'javascript']:
                    latest_code = get_js_code(container_name)
                    log_print("[DEBUG] 成功獲取最新 JavaScript 代碼")
                else:
                    latest_code = "[ERROR] 無法識別的語言類型"
                    log_print(f"[ERROR] 無法識別的語言類型: {language}")

                # 返回成功訊息和最新代碼
                final_result = f"{success_msg}\n\n[📄 最新 {language.upper()} 代碼]\n{latest_code}\n\n[除錯日誌]\n{log_capture.getvalue()}"
                return final_result

            except Exception as e:
                error_msg = f"[❌ 獲取最新代碼失敗] {str(e)}"
                log_print(error_msg)
                return f"{success_msg}\n\n{error_msg}\n\n[除錯日誌]\n{log_capture.getvalue()}"
        else:
            error_msg = f"[❌ PATCH 套用失敗]\n退出碼: {apply_result.exit_code}\n輸出: {apply_result.output.decode('utf-8').strip()}"
            log_print(error_msg)

            # 執行詳細診斷
            log_print("[DEBUG] 開始執行詳細診斷...")
            diagnose_patch_failure(container, target_file_path, diff_code, log_print)

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
