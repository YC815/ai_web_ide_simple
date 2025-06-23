from langchain.schema import HumanMessage, SystemMessage
import re
from typing import List
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
import os
from dotenv import load_dotenv

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


def create_diff(container_name, todo_list): pass


def run_sub_agent_edit_task(container_name, latest_input):
    todo_list = list_todo(latest_input)


if __name__ == "__main__":
    print(list_todo("把網頁改成現代化，新增nav，上面要寫主頁和關於我們，並且打大標題放到一張卡片裡面，卡片下面要放一個按鈕，點下去後會跳出彈出視窗，上面寫歡迎來到我的網站！"))
