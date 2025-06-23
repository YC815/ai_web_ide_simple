from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent
from langchain.schema import HumanMessage, AIMessage, BaseMessage
from langchain.tools.base import BaseTool
from langchain.agents.agent import AgentExecutor
from langchain.tools import tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from . import ai_tool

import sqlite3
from typing import List, Optional

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
    """將 diff code 套用到 container 的指定語言目錄中"""
    return ai_tool.diff_code(container_name, diff_code, language)


# ---------- Tool & Agent Management ---------- #

def get_registered_tools() -> List[BaseTool]:
    return [get_html_code, get_css_code, get_js_code, diff_code]


def build_agent_with_tools(tools: List[BaseTool]) -> AgentExecutor:
    llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant that can use tools."),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad")
    ])

    agent = create_openai_functions_agent(llm=llm, tools=tools, prompt=prompt)
    return AgentExecutor(agent=agent, tools=tools)


# ---------- SQLite Chat History ---------- #

def init_chat_session(session_id: str) -> None:
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_message_to_db(session_id: str, role: str, content: str) -> None:
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (session_id, role, content)
        VALUES (?, ?, ?)
    """, (session_id, role, content))
    conn.commit()
    conn.close()


def load_chat_history(session_id: str) -> List[BaseMessage]:
    conn = sqlite3.connect("chat_history.db")
    c = conn.cursor()
    c.execute("""
        SELECT role, content FROM messages
        WHERE session_id = ?
        ORDER BY timestamp ASC
    """, (session_id,))
    rows = c.fetchall()
    conn.close()

    messages: List[BaseMessage] = []
    for role, content in rows:
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "ai":
            messages.append(AIMessage(content=content))
    return messages


# ---------- 主聊天流程 ---------- #

def chat_with_ai(user_input: str, session_id: str) -> str:
    init_chat_session(session_id)

    tools = get_registered_tools()
    agent = build_agent_with_tools(tools)

    history = load_chat_history(session_id)
    history.append(HumanMessage(content=user_input))

    result = agent.invoke({
        "input": user_input,
        "chat_history": history
    })

    output = result.get("output", "")

    save_message_to_db(session_id, "user", user_input)
    save_message_to_db(session_id, "ai", output)

    return output

# ---------- 測試入口 ---------- #


if __name__ == "__main__":
    print("💬 AI Chat CLI")
    print("輸入你想問的內容，輸入 `exit` 離開對話。")

    session_id = input("請輸入一個 session_id（可自訂）: ").strip()
    if not session_id:
        session_id = "default-session"

    print(f"開始對話，session: {session_id}")
    print("-" * 40)

    while True:
        user_input = input("🧑 你：")
        if user_input.lower() in {"exit", "quit"}:
            print("👋 已結束對話。")
            break

        try:
            ai_response = chat_with_ai(user_input, session_id)
            print(f"🤖 AI：{ai_response}\n")
        except Exception as e:
            print(f"⚠️ 發生錯誤：{e}")
