from langchain.schema import HumanMessage, SystemMessage
import re
from typing import List
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
import os
from dotenv import load_dotenv
from . import ai_tool

load_dotenv()


def list_todo(latest_input):
    """
    分別為 HTML、CSS、JavaScript 檔案生成 TODO 清單與跨檔案注意事項（note），適合作為分三次 diff 檔生成的基礎。
    每個 TODO 與 NOTE 項目應遵守統一格式：
    - TODO 格式：{action} + {target/element} + {location or purpose}
    - NOTE 格式：{type}: {identifier} - {explanation}
      例如：css-class: card - used for general card layout
            function: showModal - displays modal on button click

    回傳格式為字典，鍵為檔案類型與 note，值為對應 TODO 列表。
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))
    file_types = [
        {
            "name": "HTML",
            "description": (
                "Break down only HTML source edits: add, modify or move HTML elements. "
                "Exclude file operations, testing or unrelated styling specifics.\n"
                "Note: Tailwind CSS is already imported via CDN. Feel free to apply styles using Tailwind utility classes directly in HTML. "
                "If specific styles are required across multiple elements or for reusability, consider naming a custom class and document it in the `note:` section."
            ),
            "examples": (
                "1. Add an empty <nav> element above the main heading\n"
                "2. Inside the <nav>, insert two anchor tags: 'Home' and 'About Us'\n"
                "3. Below the <nav>, add the HTML structure for a card component\n"
                "4. Move the existing main heading element into the card component\n"
                "❌ Locate the HTML file\n"
                "❌ Open the editor and find the <body> tag\n"
                "❌ Save the changes and refresh the browser"
            )
        },
        {
            "name": "CSS",
            "description": (
                "Break down only CSS source edits: add or adjust styles, selectors, properties. "
                "Exclude HTML structure or JS logic.\n"
                "Note: Tailwind CSS has already been imported via CDN in HTML. Only add custom CSS if Tailwind utility classes are not sufficient. "
                "If you define a new CSS class, clearly state the class name and its purpose under the `note:` section using the format: `css-class: className - description`."
            ),
            "examples": (
                "1. Add background-color and padding styles to the <nav> element using Tailwind utility classes\n"
                "2. Create a .card class using Tailwind-compatible styles only if custom behavior is required\n"
                "❌ Add a new <div> with class 'card'\n"
                "❌ Attach click event logic to trigger animation"
            )
        },
        {
            "name": "JavaScript",
            "description": (
                "Break down only JavaScript source edits: add or modify script logic, functions, event handlers. "
                "Exclude markup or styling details.\n"
                "Note: If you define any function or constant that will be reused across TODO items, please include the name and its purpose in the `note:` section using the format: `function: functionName - description`."
            ),
            "examples": (
                "1. Add a click event listener to the 'About Us' link\n"
                "2. Define a function to toggle the navigation menu\n"
                "3. Attach the toggle function to a button element\n"
                "❌ Modify <nav> layout\n"
                "❌ Change text alignment using CSS"
            )
        }
    ]

    results = {"note": []}
    for file in file_types:
        system_message = (
            f"**You are a senior process analyst specializing in web development and task breakdown.**\n\n"
            "You will receive a user request for webpage modifications. Your job is to **break down only the parts involving "
            f"{file['name']} source code edits** into clear, sequential TODO items. These items will later be used to generate step-by-step diff files.\n\n"
            "Please follow these rules:\n\n"
            "* **Do NOT include any tasks related to locating files, opening files, saving, testing, or viewing results.**\n"
            "* Focus strictly on describing the **specific code edits** that need to be made.\n"
            "* Each TODO should follow the format: `{action} + {target} + {location or purpose}`\n"
            "* Arrange all TODO items in a logical and dependency-aware execution order.\n"
            "* If no change is required for this file type, leave the result empty.\n"
            "* If there are any function names, CSS class names, or shared concepts used across TODOs, include them in a `note:` section.\n"
            "  Each note should follow the format: `type: name - explanation`, e.g., `css-class: card - used for card layout`.\n\n"
            "✅ Example TODOs:\n"
            f"{file['examples']}\n"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", HumanMessage(content=latest_input))
        ])

        response = llm.invoke(prompt.format_messages())
        content = response.content.strip()

        # 解析 TODO 清單與 note
        todo_pattern = r"^\s*\d+[\.\)]\s+(.*?)(?=\n\s*\d+[\.\)]|\Z)"
        note_pattern = r"(?i)^note\s*:\s*(.+)"

        todos = re.findall(todo_pattern, content, re.DOTALL | re.MULTILINE)
        notes = re.findall(note_pattern, content, re.DOTALL | re.MULTILINE)

        cleaned_todos = [item.strip().replace('\n', ' ') for item in todos if item.strip()]
        formatted_notes = [note.strip().replace('\n', ' ') for note in notes if note.strip()]

        results[file['name']] = cleaned_todos
        results["note"].extend(formatted_notes)

    return results


def llm_diff(container_name, todo, lang, note_ls):
    """
    生成 diff 並進行虛擬測試，如果測試失敗則回傳錯誤訊息給 AI 重新生成
    每次都重新抓取最新源碼，避免被上一輪套用後的程式變更所影響
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

    # 根據語言類型選擇對應的源碼抓取函式
    lang_mapping = {
        "HTML": "HTML",
        "CSS": "CSS",
        "JavaScript": "JavaScript",
        "JS": "JavaScript"
    }

    target_lang = lang_mapping.get(lang, lang)
    if target_lang not in ["HTML", "CSS", "JavaScript"]:
        return f"錯誤：不支援的語言類型 {lang}"

    # 最多嘗試 3 次生成 diff
    max_retries = 3
    for attempt in range(max_retries):

        # 🔄 重要：每次嘗試都重新抓取最新的源碼
        current_source = ""  # 初始化變數
        try:
            if target_lang == "HTML":
                current_source = ai_tool.get_html_code(container_name)
            elif target_lang == "CSS":
                current_source = ai_tool.get_css_code(container_name)
            elif target_lang == "JavaScript":
                current_source = ai_tool.get_js_code(container_name)
        except Exception as e:
            return f"錯誤：無法抓取 {target_lang} 源碼 - {str(e)}"

        system_message = f"""
You are given a set of TODO instructions describing modifications that need to be made to a source code file.

Your task is to write a **valid and precise unified diff** (`diff -u` format) that applies the required changes to the following source code:

```
{current_source}
```

---

### 🎯 Requirements

Your output must strictly follow the **unified diff format**, and be directly usable with Unix's `patch` tool.

---

#### 🔒 1. **HUNK HEADER IS LAW**

* Format: `@@ -old_start,old_lines +new_start,new_lines @@`
* This line defines the exact starting point and number of lines affected in both the original and modified files.

  * `old_lines`: the number of lines in the original file affected (including deletions and context)
  * `new_lines`: the number of lines in the new file (including additions and context)
* **These numbers must be 100% accurate.**

---

#### 📌 2. **CONTEXT IS MANDATORY**

* Include unchanged context lines before and after the changed lines.
* Context lines are prefixed with a space (` `).
* A diff with only additions (`+`) or only deletions (`-`) and no context will **fail**.

---

#### 🔄 3. **LINE MODIFICATIONS**

* Use `-` to remove a line:
  `- <p>Old text</p>`
* Use `+` to add a line:
  `+ <p>New text</p>`
* To replace a line, show both versions:

  ```
  - <p>Old text</p>
  + <p>New text</p>
  ```

---

#### ⚠️ 4. **EVERY LINE MUST END WITH A NEWLINE**

* Every line in the diff must be newline-terminated (`\n`).
* If your output ends in the middle of a line, the `patch` command will throw an error like:
  `patch unexpectedly ends in middle of line`

---

#### 📭 5. **IF NO MODIFICATION IS NEEDED**

* If the TODO instructions require no actual change to the source code, output:

  ```
  SKIP
  ```

---

### 🧪 Example

#### ✅ Goal: Change the `<title>` content

Original code:

```
4: <meta charset="UTF-8">
5: <title>Welcome My Website!</title>
6: </head>
```

Desired change:

* Replace line 5 with:
  `<title>Hello World!</title>`

Analysis:

* Context lines: lines 4 and 6
* Affected lines: 3 total
* Hunk header: `@@ -4,3 +4,3 @@`

✅ Final diff:

```
--- index.html
+++ index.html
@@ -4,3 +4,3 @@
    <meta charset="UTF-8">
-   <title>Welcome My Website!</title>
+   <title>Hello World!</title>
    </head>
```

{"Previous attempt failed" if attempt > 0 else ""}
{f"Error from previous attempt: {previous_error}" if attempt > 0 and 'previous_error' in locals() else ""}
"""

        # 如果是重試，添加錯誤資訊到 prompt
        if attempt > 0 and 'previous_error' in locals():
            system_message += f"\n\n⚠️ Previous attempt failed with error:\n{previous_error}\n\nPlease fix the issue and generate a corrected diff."

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("human", HumanMessage(content=todo))
        ])

        response = llm.invoke(prompt.format_messages())
        generated_diff = response.content.strip()

        # 如果 AI 回應 SKIP，直接返回
        if generated_diff.strip() == "SKIP":
            return "SKIP"

        # 虛擬測試生成的 diff
        test_result = _virtual_test_diff(container_name, generated_diff, lang)

        if test_result["success"]:
            # 測試成功，返回生成的 diff
            return generated_diff
        else:
            # 測試失敗，記錄錯誤並重試
            previous_error = test_result["error"]
            if attempt == max_retries - 1:
                # 最後一次嘗試失敗，返回錯誤
                return f"生成 diff 失敗，已嘗試 {max_retries} 次。最後錯誤：{previous_error}"

    return "生成 diff 失敗：未知錯誤"


def _virtual_test_diff(container_name, diff_code, language):
    """
    虛擬測試 diff 是否能成功套用，不實際修改檔案

    Returns:
        dict: {"success": bool, "error": str}
    """
    try:
        import docker
        import tempfile

        # 初始化 Docker 客戶端
        client = docker.from_env()
        container = client.containers.get(container_name)

        # 檢查容器狀態
        container.reload()
        if container.status != 'running':
            return {"success": False, "error": f"容器 {container_name} 狀態為 {container.status}，需要運行中狀態"}

        # 創建臨時檔案
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix=".diff", encoding='utf-8') as tmp:
            tmp.write(diff_code)
            diff_path = tmp.name

        try:
            # 上傳 patch 檔案到容器
            tar_data = ai_tool.create_tar_from_file(diff_path, "test_patch.diff")
            container.put_archive(path="/tmp", data=tar_data)

            # 根據語言類型確定目標文件路徑
            target_dir = "/usr/share/nginx/html"
            file_mapping = {
                'html': 'index.html',
                'css': 'index.css',
                'js': 'index.js',
                'javascript': 'index.js'
            }

            target_file = file_mapping.get(language.lower())
            if not target_file:
                return {"success": False, "error": f"不支援的語言類型: {language}"}

            # 執行 dry-run 測試
            dry_run_cmd = f"sh -c 'cd {target_dir} && patch --dry-run --batch --forward -p0 < /tmp/test_patch.diff'"
            dry_run_result = container.exec_run(dry_run_cmd)

            if dry_run_result.exit_code == 0:
                return {"success": True, "error": ""}
            else:
                error_output = dry_run_result.output.decode('utf-8').strip()
                return {"success": False, "error": f"Patch dry-run 失敗：{error_output}"}

        finally:
            # 清理臨時檔案
            if os.path.exists(diff_path):
                os.remove(diff_path)

    except docker.errors.NotFound:
        return {"success": False, "error": f"找不到容器: {container_name}"}
    except Exception as e:
        return {"success": False, "error": f"虛擬測試過程發生錯誤: {str(e)}"}


def create_diff(container_name, todo_list):
    """
    為每個 TODO 項目生成 diff 並自動套用到容器
    注意：每個 diff 生成前都會重新抓取最新源碼，確保基於當前狀態生成
    """
    results = []

    for lang in ["HTML", "CSS", "JavaScript"]:
        if todo_list[lang] == []:
            continue

        for todo in todo_list[lang]:
            # 生成 diff（內部會重新抓取最新源碼）
            diff_result = llm_diff(container_name, todo, lang, todo_list["note"])

            if diff_result == "SKIP":
                results.append(f"[{lang}] {todo} - 已跳過，無需修改")
            elif diff_result.startswith("錯誤") or diff_result.startswith("生成 diff 失敗"):
                results.append(f"[{lang}] {todo} - 失敗：{diff_result}")
            else:
                # diff 生成成功，嘗試套用
                apply_result = apply_diff(container_name, diff_result, lang)

                if apply_result["success"]:
                    results.append(f"[{lang}] {todo} - ✅ 成功套用")
                    if apply_result["latest_code"]:
                        results.append(f"[{lang}] 最新代碼已更新")
                else:
                    results.append(f"[{lang}] {todo} - ❌ 套用失敗：{apply_result['message']}")

    return results


def run_sub_agent_edit_task(container_name, latest_input):
    """
    執行完整的子代理編輯任務流程
    1. 根據輸入生成 TODO 清單
    2. 為每個 TODO 生成並套用 diff
    3. 回傳執行結果
    """
    try:
        # 第一步：生成 TODO 清單
        todo_list = list_todo(latest_input)

        if not todo_list or all(len(todo_list[lang]) == 0 for lang in ["HTML", "CSS", "JavaScript"]):
            return "❌ 無法生成有效的 TODO 清單，請檢查輸入內容"

        # 第二步：執行 diff 生成和套用
        results = create_diff(container_name, todo_list)

        # 格式化回傳結果
        summary = []
        summary.append("🚀 子代理編輯任務執行完成")
        summary.append("")
        summary.append("📋 TODO 清單:")

        for lang in ["HTML", "CSS", "JavaScript"]:
            if todo_list[lang]:
                summary.append(f"  [{lang}]:")
                for todo in todo_list[lang]:
                    summary.append(f"    • {todo}")

        if todo_list["note"]:
            summary.append("")
            summary.append("📝 注意事項:")
            for note in todo_list["note"]:
                summary.append(f"    • {note}")

        summary.append("")
        summary.append("⚡ 執行結果:")
        for result in results:
            summary.append(f"  {result}")

        return "\n".join(summary)

    except Exception as e:
        return f"❌ 子代理編輯任務執行失敗: {str(e)}"


def apply_diff(container_name, diff_code, language):
    """
    實際套用 diff patch 到 Docker 容器中的檔案（無 log_print 版本）

    Args:
        container_name: Docker 容器名稱
        diff_code: diff patch 內容
        language: 語言類型 (html, css, js)

    Returns:
        dict: {"success": bool, "message": str, "latest_code": str}
    """
    try:
        import docker
        import tempfile

        # 初始化 Docker 客戶端
        client = docker.from_env()
        container = client.containers.get(container_name)

        # 檢查容器狀態
        container.reload()
        if container.status != 'running':
            return {
                "success": False,
                "message": f"容器 {container_name} 狀態為 {container.status}，需要運行中狀態",
                "latest_code": ""
            }

    except docker.errors.NotFound:
        return {
            "success": False,
            "message": f"找不到容器: {container_name}",
            "latest_code": ""
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Docker 連接錯誤: {str(e)}",
            "latest_code": ""
        }

    # 創建臨時檔案
    try:
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix=".diff", encoding='utf-8') as tmp:
            tmp.write(diff_code)
            diff_path = tmp.name
    except Exception as e:
        return {
            "success": False,
            "message": f"無法創建臨時檔案: {str(e)}",
            "latest_code": ""
        }

    try:
        # 上傳 patch 檔案到容器
        tar_data = ai_tool.create_tar_from_file(diff_path, "patch.diff")
        container.put_archive(path="/tmp", data=tar_data)

        # 驗證檔案上傳
        verify_result = container.exec_run("ls -la /tmp/patch.diff")
        if verify_result.exit_code != 0:
            return {
                "success": False,
                "message": "檔案上傳驗證失敗",
                "latest_code": ""
            }

        # 根據語言類型確定目標文件路徑
        target_dir = "/usr/share/nginx/html"
        file_mapping = {
            'html': 'index.html',
            'css': 'index.css',
            'js': 'index.js',
            'javascript': 'index.js'
        }

        target_file = file_mapping.get(language.lower())
        if not target_file:
            return {
                "success": False,
                "message": f"不支援的語言類型: {language}",
                "latest_code": ""
            }

        target_file_path = f"{target_dir}/{target_file}"

        # 檢查目標文件是否存在
        file_result = container.exec_run(f"ls -la {target_file_path}")
        if file_result.exit_code != 0:
            return {
                "success": False,
                "message": f"目標文件不存在: {target_file_path}",
                "latest_code": ""
            }

        # Dry-run 測試
        dry_run_cmd = f"sh -c 'cd {target_dir} && patch --dry-run --batch --forward -p0 < /tmp/patch.diff'"
        dry_run_result = container.exec_run(dry_run_cmd)

        if dry_run_result.exit_code != 0:
            return {
                "success": False,
                "message": f"Patch dry-run 失敗: {dry_run_result.output.decode('utf-8').strip()}",
                "latest_code": ""
            }

        # 實際套用 patch
        apply_cmd = f"sh -c 'cd {target_dir} && patch --batch --forward -p0 < /tmp/patch.diff'"
        apply_result = container.exec_run(apply_cmd)

        if apply_result.exit_code == 0:
            # 套用成功，獲取最新代碼
            try:
                language_lower = language.lower()
                if language_lower == 'html':
                    latest_code = ai_tool.get_html_code(container_name)
                elif language_lower == 'css':
                    latest_code = ai_tool.get_css_code(container_name)
                elif language_lower in ['js', 'javascript']:
                    latest_code = ai_tool.get_js_code(container_name)
                else:
                    latest_code = "無法識別的語言類型"

                return {
                    "success": True,
                    "message": f"Patch 套用成功: {apply_result.output.decode('utf-8').strip()}",
                    "latest_code": latest_code
                }
            except Exception as e:
                return {
                    "success": True,
                    "message": f"Patch 套用成功，但獲取最新代碼失敗: {str(e)}",
                    "latest_code": ""
                }
        else:
            return {
                "success": False,
                "message": f"Patch 套用失敗: {apply_result.output.decode('utf-8').strip()}",
                "latest_code": ""
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"套用過程發生錯誤: {str(e)}",
            "latest_code": ""
        }
    finally:
        # 清理臨時檔案
        try:
            if os.path.exists(diff_path):
                os.remove(diff_path)
        except:
            pass


if __name__ == "__main__":
    print(list_todo("把網頁改成現代化，新增nav，上面要寫主頁和關於我們，並且打大標題放到一張卡片裡面，卡片下面要放一個按鈕，點下去後會跳出彈出視窗，上面寫歡迎來到我的網站！"))
