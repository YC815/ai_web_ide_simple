# 專案規劃

## 前端

---

## 後端

### AI Tool

- Get_HTML_Code

```
Input:
Output: HTML Code
```

- Get_CSS_Code

```
Input:
Output: CSS Code
```

- GET_JS_Code

```
Input:
Output: JS Code
```

- Diff Code

```
Input:
   1. HTML / JS / CSS
   2. Diff
Output: Success Message / Error Message
```

### 系統 Function

- 列出 Docker
- 安裝 Docker
  - 內部要設置好 index.html, index.css, index.js

### AI Chat

- 資料存儲: Sqlite
- 架構: LangChain

---

## Note

- 後端使用 Python
- Docker 內部灌好 index.html, index.css, index.js

---

## 想像

- HomePage

```
上面有創建新容器按鈕
下面列出所有目前的容器以及搭配的「進入容器」按鈕，點擊之後將docker容器資訊記錄下來
```

## 檔案修改架構

1. 主 Agent 判斷若為需求就將需求訊息轉到副 Agent
2. 副 Agent 針對 HTML, CSS, JavaScript 三個檔案生成相關 TODO
3. 跑迴圈，迴圈規則：
   檔案種類（HTML, CSS, JavaScript）先跑，如果該檔案 TODO 為空就跳過該檔案種類。
   每一種檔案從第一項 todo 生成 diff or "SKIP"。
   如果是 SKIP 那就跳過此輪迴圈。
   如果是 diff 就套用 diff。
   如果出錯就將錯誤訊息返還給 AI 並重新生成一遍 diff。
   如果超過四次無法套用 diff 就跳錯。
4. 迴圈跑完後返回成功訊息或錯誤訊息給主 Agent。
5. 如果跳錯，主 Agent 提示 User 說我們已經盡力拆分任務，修改依然太過複雜，請 User 主動拆分任務。
