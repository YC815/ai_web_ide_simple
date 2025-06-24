# AI Web IDE

一個基於人工智慧的網頁開發整合環境，讓您透過自然語言對話來創建和修改網頁專案。

## 🚀 專案概述

AI Web IDE 是一個創新的網頁開發工具，結合了：

- **AI 對話系統**：使用 OpenAI GPT-4o 模型
- **Docker 容器化**：每個專案運行在獨立的 Nginx 容器中
- **智能代碼編輯**：AI 自動生成並套用程式碼修改
- **即時預覽**：支援 HTML、CSS、JavaScript 的即時編輯和預覽

## 🏗️ 系統架構

### 核心組件

1. **Flask Web 應用程式** (`app.py`)

   - 提供 Web 使用者介面
   - 處理 HTTP 請求和路由
   - 管理使用者會話

2. **AI 聊天系統** (`Functions/ai_chat.py`)

   - 與 OpenAI GPT-4o 整合
   - 管理聊天歷史（SQLite）
   - 專案特定的對話會話
   - LangChain Agent 工具系統

3. **AI 工具模組** (`Functions/ai_tool.py`)

   - Docker 容器程式碼讀取
   - 編輯請求處理
   - 與子代理系統整合

4. **子代理系統** (`Functions/sub_agent.py`)

   - 智能任務分解
   - 自動生成 Unified Diff
   - 程式碼自動套用和測試

5. **系統管理** (`Functions/system.py`)
   - Docker 容器生命週期管理
   - 專案建立和配置
   - 埠口管理

## 🛠️ 主要功能

### 專案管理

- **建立專案**：自動建立 Docker 容器和基礎檔案結構
- **啟動/停止**：管理專案容器的運行狀態
- **刪除專案**：安全移除專案和相關資源

### AI 驅動開發

- **自然語言編程**：用中文描述需求，AI 自動生成程式碼
- **智能任務分解**：將複雜需求拆分為 HTML、CSS、JavaScript 任務
- **自動代碼套用**：生成並測試 diff，自動套用到專案檔案

### 對話系統

- **專案特定對話**：每個專案維護獨立的對話歷史
- **多會話支援**：支援同一專案的多個對話會話
- **串流回應**：即時顯示 AI 處理狀態

### 程式碼管理

- **即時讀取**：隨時查看專案的 HTML、CSS、JavaScript 程式碼
- **版本控制**：透過 diff 系統精確控制程式碼變更
- **虛擬測試**：在套用前測試程式碼變更

## 🚀 快速開始

### 環境需求

- Python 3.13.3
- Docker 和 Docker Compose
- OpenAI API 金鑰

### 安裝步驟

1. **複製專案**

   ```bash
   git clone https://github.com/YC815/ai_web_ide_simple
   cd ai_web_ide
   ```

2. **安裝相依套件**

   ```bash
   pip install -r requirements.txt
   ```

3. **設定環境變數**
   建立 `.env` 檔案：

   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ```

4. **啟動應用程式**

   ```bash
   python app.py
   ```

5. **開啟瀏覽器**
   訪問 `http://localhost:5001`

### 使用流程

1. **建立新專案**

   - 在首頁點擊「建立新專案」
   - 輸入專案名稱（僅支援英文、數字、底線、連字號）

2. **開始對話**

   - 選擇專案進入對話介面
   - 用自然語言描述您的需求

3. **AI 自動開發**

   - AI 會分析您的需求
   - 自動產生對應的程式碼修改
   - 即時套用到專案中

4. **預覽結果**
   - 點擊專案埠口連結預覽網頁
   - 繼續與 AI 對話進行調整

## 🔧 技術細節

### AI 工具系統

系統提供以下 AI 工具：

- `get_html_code()`: 讀取 HTML 程式碼
- `get_css_code()`: 讀取 CSS 程式碼
- `get_js_code()`: 讀取 JavaScript 程式碼
- `edit_request()`: 執行程式碼編輯任務

### 子代理工作流程

1. **任務分解** (`list_todo()`)

   - 分析使用者需求
   - 產生 HTML、CSS、JavaScript 的 TODO 清單
   - 識別跨檔案的共用元素

2. **Diff 生成** (`llm_diff()`)

   - 為每個 TODO 產生精確的 Unified Diff
   - 支援虛擬測試確保 patch 可用性
   - 最多重試 3 次確保品質

3. **自動套用** (`apply_diff()`)
   - 上傳 patch 到 Docker 容器
   - 執行 dry-run 測試
   - 實際套用程式碼變更

### 資料庫結構

使用 SQLite 儲存聊天歷史：

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    project_name TEXT,
    role TEXT,
    content TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Docker 容器配置

每個專案使用獨立的 Nginx 容器：

- 基於 `nginx:alpine` 映像
- 安裝 `patch` 工具支援程式碼修改
- 動態埠口分配（從 8080 開始）

## 🎯 使用範例

### 範例 1：建立基礎網頁

```
使用者：「幫我建立一個簡單的個人網站，要有導航列和自我介紹」

AI 會自動：
1. 分析需求並產生 TODO 清單
2. 修改 HTML 結構添加 nav 和內容區塊
3. 使用 Tailwind CSS 添加樣式
4. 產生對應的 JavaScript 互動功能
```

### 範例 2：新增互動功能

```
使用者：「在網頁中加入一個按鈕，點擊後顯示彈出視窗」

AI 會自動：
1. 在 HTML 中添加按鈕元素
2. 設計彈出視窗的 CSS 樣式
3. 實作 JavaScript 點擊事件處理
```

## 🔒 安全性考量

- **容器隔離**：每個專案運行在獨立的 Docker 容器中
- **埠口管理**：自動分配可用埠口避免衝突
- **輸入驗證**：專案名稱格式檢查防止注入攻擊
- **資源清理**：自動清理暫存檔案和容器資源

## 🛠️ 自訂配置

### 日誌設定

在 `app.py` 中調整日誌模式：

```python
log_to_file = True  # 啟用檔案日誌
```

### AI 模型設定

在 `Functions/ai_chat.py` 中更改模型：

```python
llm = ChatOpenAI(model="gpt-4o", temperature=0)
```

## 🚨 故障排除

### 常見問題

1. **容器無法啟動**

   - 檢查 Docker 服務是否運行
   - 確認埠口未被佔用

2. **AI 回應錯誤**

   - 驗證 OpenAI API 金鑰
   - 檢查網路連接

3. **程式碼套用失敗**
   - 查看容器日誌
   - 確認 patch 工具已安裝

## 🤝 貢獻指南

歡迎提交 Issue 和 Pull Request！

### 開發環境設定

1. Fork 本專案
2. 建立功能分支
3. 提交變更
4. 建立 Pull Request

## 📄 授權條款

本專案採用 MIT 授權條款。

## 📞 聯絡資訊

如有問題或建議，請透過 GitHub Issues 聯絡我們。

---

**AI Web IDE** - 讓 AI 成為您的編程夥伴 🤖✨
