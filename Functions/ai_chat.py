from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent
from langchain.schema import HumanMessage, AIMessage, BaseMessage
from langchain.tools.base import BaseTool
from langchain.agents.agent import AgentExecutor
from langchain.tools import tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from . import ai_tool
from . import sub_agent
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
def edit_request(container_name: str, session_id: str, project_name: Optional[str] = None) -> str:
    """執行代碼編輯任務

    當使用者請求修改網頁內容、樣式或功能時，使用此工具。
    工具會自動：
    1. 分析使用者的最新請求
    2. 生成對應的 HTML、CSS、JavaScript 修改計劃
    3. 自動執行所有必要的代碼變更
    4. 回報執行結果

    Parameters:
    - container_name: Docker 容器名稱
    - session_id: 當前聊天會話 ID
    - project_name: 專案名稱（可選）
    """
    return ai_tool.edit_request(container_name, session_id, project_name)


# ---------- Tool & Agent Management ---------- #

def get_registered_tools() -> List[BaseTool]:
    return [get_html_code, get_css_code, get_js_code, edit_request]


def build_agent_with_tools(
    tools: List[BaseTool], project_name: Optional[str] = None
) -> AgentExecutor:
    llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

    system_message = """You are a helpful assistant that can use tools to interact with Docker containers.

All responses and explanations must be written in Traditional Chinese.

When using tools that require a 'container_name' parameter, you MUST provide the container name.

🔧 **主要工作流程**：
1. 當使用者詢問或要求查看代碼時，使用對應的查看工具 (get_html_code, get_css_code, get_js_code)
2. 當使用者要求修改、編輯、改進網頁時，直接使用 edit_request 工具

⚡ **重要指引**：
- 如果使用者的請求涉及任何代碼修改、網頁編輯、樣式調整、功能添加等，請直接使用 edit_request 工具
- edit_request 工具會自動處理所有必要的代碼變更，無需你手動生成 diff 或指定文件類型
- 只有在使用者明確要求查看當前代碼內容時，才使用 get_* 系列工具

IMPORTANT: For CSS styling preferences, the sub-agent will prefer using Tailwind CSS utility classes for better consistency and aesthetics.
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
For all tools that require parameters, the system will automatically provide the correct values.

🎯 **可用工具說明**：
- get_html_code(container_name): 查看 HTML 代碼及行數 - 自動使用 container_name='{container_name}'
- get_css_code(container_name): 查看 CSS 代碼及行數 - 自動使用 container_name='{container_name}'
- get_js_code(container_name): 查看 JavaScript 代碼及行數 - 自動使用 container_name='{container_name}'
- edit_request(container_name, session_id, project_name): 執行代碼編輯任務 - 系統自動填入所有參數

📝 **使用範例**：
- 查看 HTML：get_html_code(container_name='{container_name}')
- 執行編輯任務：edit_request(container_name='{container_name}', session_id='current_session', project_name='{project_name}')

🚀 **編輯任務工作流程**：
1. 當使用者要求修改時，直接調用 edit_request 工具
2. 系統會自動：
   - 分析使用者請求
   - 生成修改計劃
   - 執行所有必要的代碼變更
   - 回報結果
3. 你只需要向使用者解釋執行結果即可

⚠️ **重要**：edit_request 工具的所有參數都會由系統自動填入，你不需要猜測或指定 session_id 和 project_name 的具體值。
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

    # 包裝工具以捕獲調用過程並自動注入參數
    original_tools = agent_executor.tools
    wrapped_tools = []

    for tool in original_tools:
        def create_wrapped_tool(original_tool):
            def wrapped_func(*args, **kwargs):
                print(f"[TOOL_CALL] 開始調用工具: {original_tool.name}")

                # 特殊處理 edit_request 工具，自動注入參數
                if original_tool.name == 'edit_request':
                    # 自動填入 session_id 和 project_name
                    kwargs['session_id'] = session_id
                    kwargs['project_name'] = project_name
                    print(f"[TOOL_CALL] edit_request 自動注入參數: session_id={session_id}, project_name={project_name}")

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
        'edit_request': '正在執行代碼編輯任務...'
    }

    # 包裝工具以自動注入參數
    original_tools = agent_executor.tools
    wrapped_tools = []

    for tool in original_tools:
        def create_wrapped_tool(original_tool):
            def wrapped_func(*args, **kwargs):
                # 特殊處理 edit_request 工具，自動注入參數
                if original_tool.name == 'edit_request':
                    kwargs['session_id'] = session_id
                    kwargs['project_name'] = project_name
                    if status_callback:
                        status_callback("正在執行代碼編輯任務...")

                return original_tool.func(*args, **kwargs)

            # 保持原有的工具屬性
            wrapped_func.name = original_tool.name
            wrapped_func.description = original_tool.description
            return wrapped_func

        # 建立包裝後的工具
        from langchain.tools import tool as tool_decorator
        wrapped_tool = tool_decorator(
            description=tool.description
        )(create_wrapped_tool(tool))
        wrapped_tool.name = tool.name
        wrapped_tools.append(wrapped_tool)

    # 更新 agent_executor 的工具
    agent_executor.tools = wrapped_tools

    if status_callback:
        status_callback("AI 正在分析您的請求...")

    print("[AI_CHAT_STREAM] 開始執行 agent...")
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
