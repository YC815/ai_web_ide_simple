from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent
from langchain.schema import HumanMessage, AIMessage, BaseMessage
from langchain.tools.base import BaseTool
from langchain.agents.agent import AgentExecutor
from langchain.tools import tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from . import ai_tool
from . import diff_tool
import sqlite3
from typing import List, Optional, Tuple

from dotenv import load_dotenv
import os

load_dotenv()

# ---------- Tool definitions ---------- #


@tool
def get_html_code(container_name: str) -> str:
    """取得 container 中的 HTML 原始碼"""
    return ai_tool.get_html_code(container_name)


@tool
def get_css_code(container_name: str) -> str:
    """取得 container 中的 CSS 原始碼"""
    return ai_tool.get_css_code(container_name)


@tool
def get_js_code(container_name: str) -> str:
    """取得 container 中的 JavaScript 原始碼"""
    return ai_tool.get_js_code(container_name)


@tool
def diff_code(container_name: str, diff_code: str, language: str) -> str:
    """將 unified diff patch 套用到 container 的指定文件中

    Parameters:
    - container_name: Docker 容器名稱
    - diff_code: 要套用的 unified diff patch 內容（必須是 unified diff 格式）
    - language: 文件類型，必須是 'html', 'css', 或 'js'

    CRITICAL: diff_code 參數必須是 unified diff 格式，例如：
    ```
    --- index.html
    +++ index.html
    @@ -6,1 +6,1 @@
    -    <title>Old Title</title>
    +    <title>New Title</title>
    ```

    根據使用者的需求選擇正確的 language 參數：
    - 'html': 用於修改頁面結構、文字內容、HTML 元素
    - 'css': 用於修改樣式、顏色、佈局、字體等視覺效果
    - 'js': 用於修改 JavaScript 功能、互動行為、動態效果
    """
    return diff_tool.diff_code(container_name, diff_code, language)


# ---------- Tool & Agent Management ---------- #

def get_registered_tools() -> List[BaseTool]:
    return [get_html_code, get_css_code, get_js_code, diff_code]


def build_agent_with_tools(
    tools: List[BaseTool], project_name: Optional[str] = None
) -> AgentExecutor:
    llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

    system_message = """You are a helpful assistant that can use tools to interact with Docker containers.

All responses and explanations must be written in Traditional Chinese.

When using tools that require a 'container_name' parameter, you MUST provide the container name.

As an expert in the `patch` utility, you must follow these strict rules for the `diff_code` tool to prevent "malformed patch" errors.

**CRITICAL: Rules for `diff_code`**

1.  **HUNK HEADER `@@ ... @@` IS LAW**:
    *   Format: `@@ -old_start,old_lines +new_start,new_lines @@`
    *   This header dictates the entire change. `old_lines` is the count of original lines affected (removals + context). `new_lines` is the count for the new file (additions + context).
    *   **Your line counts MUST BE PERFECT.**

2.  **CONTEXT IS MANDATORY & NON-NEGOTIABLE**:
    *   You MUST provide unchanged context lines (prefixed with a space ` `) before and after your changes.
    *   `patch` uses context to find the location. No context, no patch.
    *   A diff with only `+` (add) lines is almost always **WRONG** and will fail because `patch` does not know where to insert them.

3.  **REMOVING & ADDING LINES**:
    *   Remove a line with `-`: `- <p>Old</p>`
    *   Add a line with `+`: `+ <p>New</p>`
    *   To replace, use `-` then `+`.

4.  **EVERY LINE REQUIRES A NEWLINE (`\n`)**:
    *   The `patch unexpectedly ends in middle of line` error is caused by a missing `\n`.
    *   The entire `diff_code` string MUST end with `\n`.

**WORKFLOW & EXAMPLE**

Goal: Change the `<title>` in the HTML.

1.  **`get_html_code()`**: First, get the current code with line numbers.
    ```
    ...
    4: <meta charset="UTF-8">
    5: <title>Welcome My Website!</title>
    6: </head>
    ...
    ```

2.  **Analyze & Plan**:
    *   **Change**: Replace line 5.
    *   **Context**: Use line 4 as leading context and line 6 as trailing context.
    *   **Hunk Header**: The change starts at line 4. It affects 3 lines in the original (`<meta>`, old `<title>`, `</head>`). It will also be 3 lines in the new version. So, `@@ -4,3 +4,3 @@`.

3.  **Construct `diff_code`**:
    ```
    --- index.html
    +++ index.html
    @@ -4,3 +4,3 @@
     <meta charset="UTF-8">
    -    <title>Welcome My Website!</title>
    +    <title>Hello World!</title>
     </head>
    ```
    *Notice the space ` ` before context lines, `-` before removed, `+` before added. The indentation of the original file must be preserved.*

Analyze the user's request to determine which file type should be modified:
- Title, content, structure changes → 'html'
- Visual appearance, styling changes → 'css' 
- Interactive behavior, functionality → 'js'

IMPORTANT: For CSS styling, **you should prefer using Tailwind CSS** utility classes for better consistency and aesthetics. Avoid writing plain or raw CSS whenever possible.
"""

    if project_name:
        # 智能處理容器名稱 - 如果 project_name 已經包含完整的容器名稱，直接使用
        if project_name.startswith('ai-web-ide_') and project_name.endswith('_container'):
            container_name = project_name
            print(f"[AGENT_BUILD] 使用完整容器名稱: {container_name}")
        else:
            container_name = f'ai-web-ide_{project_name}_container'
            print(f"[AGENT_BUILD] 生成容器名稱: {container_name} (來自專案: {project_name})")

        system_message += f"""
You are currently working on the project '{project_name}'.
For all tools that require a 'container_name' parameter, use '{container_name}' as the container name.

CRITICAL: When calling ANY tool, you MUST provide the container_name parameter with the value: '{container_name}'

Available tools:
- get_html_code(container_name): Gets HTML code with line numbers from the container - MUST use container_name='{container_name}'
- get_css_code(container_name): Gets CSS code with line numbers from the container - MUST use container_name='{container_name}'
- get_js_code(container_name): Gets JavaScript code with line numbers from the container - MUST use container_name='{container_name}'
- diff_code(container_name, diff_code, language): Applies UNIFIED diff patches to container files - MUST use container_name='{container_name}'

EXAMPLES:
- To get HTML with line numbers: get_html_code(container_name='{container_name}')
- To apply a diff, follow the detailed workflow in the main instructions. A valid example is:
  diff_code(container_name='{container_name}', diff_code='--- index.html\\n+++ index.html\\n@@ -4,3 +4,3 @@\\n <meta charset="UTF-8">\\n-    <title>Welcome My Website!</title>\\n+    <title>Hello World!</title>\\n </head>', language='html')

WORKFLOW for making changes:
1. First call get_html_code(container_name='{container_name}') to see current content with line numbers
2. Identify the exact line numbers to modify AND the surrounding context lines
3. Calculate hunk header: count original lines (including context) and new lines (including context)
4. Create unified diff format with proper context lines before and after changes
5. Ensure diff ends with newline and uses correct prefixes ('-', '+', ' ')
6. Apply with diff_code(container_name='{container_name}', diff_code='...', language='html')

CRITICAL: Always include 1-3 context lines before and after your changes, and ensure line counts in hunk header are accurate!

Remember: ALWAYS provide the container_name='{container_name}' parameter when calling these tools.
"""
    else:
        system_message += """
No project is currently selected. You need to ask the user for the project name or container name before using any tools.
"""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_message),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    agent = create_openai_functions_agent(llm=llm, tools=tools, prompt=prompt)
    return AgentExecutor(agent=agent, tools=tools)


# ---------- 專案相關的 session 管理 ---------- #

def create_project_session_id(session_id: str, project_name: Optional[str] = None) -> str:
    """
    建立專案特定的 session ID
    格式：project_name::session_id 或直接使用 session_id（如果沒有專案名稱）
    """
    if project_name:
        return f"{project_name}::{session_id}"
    return session_id


def parse_project_session_id(full_session_id: str) -> Tuple[Optional[str], str]:
    """
    解析專案 session ID
    回傳：(project_name, session_id)
    """
    if "::" in full_session_id:
        project_name, session_id = full_session_id.split("::", 1)
        return project_name, session_id
    return None, full_session_id


# ---------- SQLite Chat History ---------- #

def init_chat_session(session_id: str, project_name: Optional[str] = None) -> None:
    """初始化聊天 session，支援專案分離"""
    full_session_id = create_project_session_id(session_id, project_name)

    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()

    # 創建訊息表（如果不存在）
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 檢查是否需要添加 project_name 欄位（資料庫遷移）
    try:
        c.execute("SELECT project_name FROM messages LIMIT 1")
    except sqlite3.OperationalError:
        # project_name 欄位不存在，需要添加
        print("[INFO] 升級資料庫結構：添加 project_name 欄位")
        c.execute("ALTER TABLE messages ADD COLUMN project_name TEXT")
        conn.commit()

    # 檢查 session 是否已存在
    c.execute("SELECT 1 FROM messages WHERE session_id = ?", (full_session_id,))
    if c.fetchone() is None:
        # 初始化新的 session
        c.execute(
            "INSERT INTO messages (session_id, project_name, role, content) VALUES (?, ?, ?, ?)",
            (full_session_id, project_name, "system", f"Session initialized for project: {project_name or 'default'}"),
        )

    conn.commit()
    conn.close()


def save_message_to_db(session_id: str, role: str, content: str, project_name: Optional[str] = None) -> None:
    """儲存訊息到資料庫，支援專案分離"""
    full_session_id = create_project_session_id(session_id, project_name)

    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (session_id, project_name, role, content)
        VALUES (?, ?, ?, ?)
    """, (full_session_id, project_name, role, content))
    conn.commit()
    conn.close()


def load_chat_history(session_id: str, project_name: Optional[str] = None) -> List[BaseMessage]:
    """載入聊天歷史，支援專案分離"""
    full_session_id = create_project_session_id(session_id, project_name)

    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("""
        SELECT role, content FROM messages
        WHERE session_id = ?
        ORDER BY timestamp ASC
    """, (full_session_id,))
    rows = c.fetchall()
    conn.close()

    messages: List[BaseMessage] = []
    for role, content in rows:
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "ai":
            messages.append(AIMessage(content=content))
    return messages


def get_all_sessions() -> List[dict]:
    """從資料庫中取得所有 session，按專案分組並按最後訊息時間排序，只包含有真正對話內容的 session"""
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    try:
        # 修改查詢條件，排除只有 system 訊息的 session
        c.execute("""
            SELECT session_id, project_name, MAX(timestamp) as last_message_time
            FROM messages
            WHERE role != 'system'
            GROUP BY session_id
            HAVING COUNT(*) > 0
            ORDER BY last_message_time DESC
        """)
        rows = c.fetchall()

        sessions = []
        for session_id, project_name, last_message_time in rows:
            # 解析 session_id 來取得原始的 session_id
            parsed_project, parsed_session = parse_project_session_id(session_id)

            sessions.append({
                'session_id': parsed_session,
                'full_session_id': session_id,
                'project_name': project_name or parsed_project,
                'last_message_time': last_message_time
            })

        return sessions
    except sqlite3.OperationalError:
        # 如果資料庫或資料表不存在，回傳空列表
        return []
    finally:
        conn.close()


def get_sessions_by_project(project_name: str) -> List[dict]:
    """取得特定專案的所有 session，只包含有真正對話內容的 session"""
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    try:
        # 修改查詢條件，排除只有 system 訊息的 session
        c.execute("""
            SELECT session_id, MAX(timestamp) as last_message_time
            FROM messages
            WHERE project_name = ? AND role != 'system'
            GROUP BY session_id
            HAVING COUNT(*) > 0
            ORDER BY last_message_time DESC
        """, (project_name,))
        rows = c.fetchall()

        sessions = []
        for session_id, last_message_time in rows:
            # 解析 session_id 來取得原始的 session_id
            _, parsed_session = parse_project_session_id(session_id)

            sessions.append({
                'session_id': parsed_session,
                'full_session_id': session_id,
                'project_name': project_name,
                'last_message_time': last_message_time
            })

        return sessions
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


def delete_session(session_id: str, project_name: Optional[str] = None) -> None:
    """從資料庫中刪除指定 session 的所有訊息，支援專案分離"""
    full_session_id = create_project_session_id(session_id, project_name)

    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE session_id = ?", (full_session_id,))
    conn.commit()
    conn.close()


def get_project_list() -> List[str]:
    """取得所有有聊天記錄的專案列表"""
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    try:
        c.execute("""
            SELECT DISTINCT project_name
            FROM messages
            WHERE project_name IS NOT NULL AND project_name != ''
            ORDER BY project_name
        """)
        rows = c.fetchall()
        return [row[0] for row in rows if row[0]]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


# ---------- 主聊天流程 ---------- #

def chat_with_ai(
    user_input: str, session_id: str, project_name: Optional[str] = None
) -> str:
    """主聊天函數，支援專案分離"""
    print(f"[AI_CHAT] 開始處理聊天請求 - 專案: {project_name}")

    # 初始化 session（包含專案資訊）
    init_chat_session(session_id, project_name)

    # 取得歷史訊息（專案特定）
    history = load_chat_history(session_id, project_name)
    print(f"[AI_CHAT] 載入聊天歷史，共 {len(history)} 條訊息")

    # 建立 agent
    tools = get_registered_tools()
    print(f"[AI_CHAT] 建立 agent，可用工具: {[tool.name for tool in tools]}")

    agent_executor = build_agent_with_tools(tools, project_name)

    # 包裝工具以捕獲調用過程
    original_tools = agent_executor.tools
    wrapped_tools = []

    for tool in original_tools:
        def create_wrapped_tool(original_tool):
            def wrapped_func(*args, **kwargs):
                print(f"[TOOL_CALL] 開始調用工具: {original_tool.name}")
                print(f"[TOOL_CALL] 參數: args={args}, kwargs={kwargs}")
                try:
                    result = original_tool.func(*args, **kwargs)
                    print(f"[TOOL_CALL] 工具 {original_tool.name} 執行成功")
                    print(f"[TOOL_RESULT] 結果: {result[:500]}...")  # 只顯示前500字元，避免過長
                    return result
                except Exception as e:
                    print(f"[TOOL_ERROR] 工具 {original_tool.name} 執行失敗: {str(e)}")
                    raise e

            # 保持原有的工具屬性
            wrapped_func.name = original_tool.name
            wrapped_func.description = original_tool.description
            return wrapped_func

        # 建立包裝後的工具
        from langchain.tools import tool as tool_decorator
        wrapped_tool = tool_decorator(
            description=tool.description
        )(create_wrapped_tool(tool))
        # 手動設定工具名稱
        wrapped_tool.name = tool.name
        wrapped_tools.append(wrapped_tool)

    # 更新 agent_executor 的工具
    agent_executor.tools = wrapped_tools

    print("[AI_CHAT] 開始執行 agent...")
    # 執行 agent
    response = agent_executor.invoke(
        {
            "input": user_input,
            "chat_history": history,
        }
    )

    # 儲存 AI 回覆（包含專案資訊）
    ai_response = response.get("output", "")
    print(f"[AI_CHAT] Agent 執行完成，回應長度: {len(ai_response)} 字元")

    save_message_to_db(session_id, "user", user_input, project_name)
    save_message_to_db(session_id, "ai", ai_response, project_name)

    return ai_response


def chat_with_ai_stream(
    user_input: str,
    session_id: str,
    project_name: Optional[str] = None,
    status_callback=None
) -> str:
    """主聊天函數，支援專案分離和狀態回調"""
    print(f"[AI_CHAT_STREAM] 開始處理 streaming 聊天請求 - 專案: {project_name}")

    # 初始化 session（包含專案資訊）
    init_chat_session(session_id, project_name)

    # 取得歷史訊息（專案特定）
    history = load_chat_history(session_id, project_name)
    print(f"[AI_CHAT_STREAM] 載入聊天歷史，共 {len(history)} 條訊息")

    # 建立 agent
    tools = get_registered_tools()
    print(f"[AI_CHAT_STREAM] 建立 agent，可用工具: {[tool.name for tool in tools]}")

    agent_executor = build_agent_with_tools(tools, project_name)

    # 建立工具名稱映射表
    tool_name_map = {
        'get_html_code': '正在讀取 HTML 代碼...',
        'get_css_code': '正在讀取 CSS 代碼...',
        'get_js_code': '正在讀取 JavaScript 代碼...',
        'diff_code': '正在套用代碼變更...'
    }

    # 為了避免遞迴問題，我們使用一個簡單的回調包裝方式
    # 保存原始工具，然後在執行時進行狀態回調
    if status_callback:
        status_callback("AI 正在分析您的請求...")

    print("[AI_CHAT_STREAM] 開始執行 agent...")

    # 我們不再包裝工具，直接使用原始的 agent_executor
    # 這避免了遞迴問題，狀態更新將通過其他方式處理
    response = agent_executor.invoke(
        {
            "input": user_input,
            "chat_history": history,
        }
    )

    # 儲存 AI 回覆（包含專案資訊）
    ai_response = response.get("output", "")
    print(f"[AI_CHAT_STREAM] Agent 執行完成，回應長度: {len(ai_response)} 字元")

    save_message_to_db(session_id, "user", user_input, project_name)
    save_message_to_db(session_id, "ai", ai_response, project_name)

    return ai_response


def get_latest_user_message(session_id: str, project_name: Optional[str] = None) -> Optional[str]:
    """
    從 chat_history 中抓取最新一筆 HumanMessage（使用者輸入）
    """
    history = load_chat_history(session_id, project_name)
    for msg in reversed(history):
        if isinstance(msg, HumanMessage):
            return msg.content
    return None


# ---------- 測試入口 ---------- #
if __name__ == "__main__":
    print("💬 AI Chat CLI")
    print("輸入你想問的內容，輸入 `exit` 離開對話。")

    session_id = input("請輸入一個 session_id（可自訂）: ").strip()
    if not session_id:
        session_id = "default-session"

    project_name = input("請輸入專案名稱（可選，按 Enter 跳過）: ").strip()
    if not project_name:
        project_name = None

    print(f"開始對話，session: {session_id}, 專案: {project_name or '無'}")
    print("-" * 40)

    while True:
        user_input = input("🧑 你：")
        if user_input.lower() in {"exit", "quit"}:
            print("👋 已結束對話。")
            break

        try:
            ai_response = chat_with_ai(user_input, session_id, project_name)
            print(f"🤖 AI：{ai_response}\n")
        except Exception as e:
            print(f"⚠️ 發生錯誤：{e}")
