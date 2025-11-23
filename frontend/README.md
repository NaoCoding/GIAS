# GIAS Frontend - GitHub Issue Analysis System

一個輕量級的 React 前端應用，用於與 GIAS 後端互動，提供 GitHub 問題分析和通用查詢功能。

## 功能特性

### 1. 通用查詢頁面 (Query Page)
- 向 AI 代理提出任何關於代碼庫的問題
- 實時處理和展示結果
- 支持長文本查詢

### 2. GitHub 問題分析頁面 (Issue Analysis Page)
- 輸入 GitHub repository 信息 (owner/repo/issue_id)
- 自動獲取 GitHub 問題內容
- 支持自定義查詢或使用問題原文進行分析
- **構建 RAG 功能**：為特定 repository 構建知識庫，自動索引所有文檔

## 技術棧

- **React 18** - UI 框架
- **Vite** - 輕量級構建工具（比 Create React App 快）
- **Axios** - HTTP 客戶端
- **CSS3** - 原生樣式（無 CSS 框架依賴）

## 安裝與運行

### 前置要求
- Node.js 16+
- npm 或 yarn
- GIAS 後端運行於 `http://localhost:8000`

### 安裝依賴
```bash
cd frontend
npm install
```

### 開發模式
```bash
npm run dev
```
應用將運行於 `http://localhost:3000`

### 構建生產版本
```bash
npm run build
```
輸出文件位於 `dist/` 目錄

### 預覽生產構建
```bash
npm run preview
```

## 項目結構

```
frontend/
├── index.html                 # HTML 入口模板
├── package.json              # 項目配置
├── vite.config.js            # Vite 配置
├── src/
│   ├── main.jsx             # React 應用入口
│   ├── App.jsx              # 主應用組件
│   ├── App.css              # 全局樣式
│   ├── api.js               # API 服務層
│   ├── pages/
│   │   ├── QueryPage.jsx    # 通用查詢頁面
│   │   └── IssueAnalysisPage.jsx  # GitHub 問題分析頁面
│   └── styles/
│       ├── QueryPage.css    # 查詢頁面樣式
│       └── IssueAnalysisPage.css  # 問題分析頁面樣式
```

## API 接口

前端與後端通信的主要接口：

### 1. 通用查詢
```
POST /api/query
{
  "query": "your question here"
}
```

### 2. 分析 GitHub 問題
```
POST /api/analyze-issue
{
  "owner": "repository_owner",
  "repo": "repository_name",
  "issue_id": 123,
  "query": "optional custom query"
}
```

### 3. 構建 RAG 知識庫
```
POST /api/build-rag
{
  "owner": "repository_owner",
  "repo": "repository_name"
}
```

## 使用示例

### 查詢頁面
1. 導航至 "Query" 標籤
2. 輸入問題
3. 點擊 "Ask Question" 按鈕
4. 查看 AI 的回應

### 問題分析頁面
1. 導航至 "Analyze Issue" 標籤
2. 輸入 GitHub repository 所有者名稱
3. 輸入 repository 名稱
4. 輸入問題 ID
5. （可選）輸入自定義查詢
6. 點擊 "Analyze Issue" 按鈕
7. 查看分析結果並可點擊 "View on GitHub" 查看原始問題

**構建 RAG 流程：**
1. 填入 owner 和 repo 字段
2. 點擊 "Build RAG for Repo" 按鈕
3. 等待系統索引所有文檔
4. 成功後會顯示索引文檔數量

## 環境配置

在 `vite.config.js` 中已配置代理，將 `/api` 請求轉發到後端：

```javascript
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  }
}
```

如需修改後端地址，在 `src/api.js` 中更新 `API_BASE_URL`

## 特性說明

### 最小化依賴
- 僅使用 React、React DOM 和 Axios
- 無額外 UI 框架（Bootstrap、Tailwind 等）
- 純 CSS3 樣式，便於自定義

### 響應式設計
- 支持桌面、平板和手機設備
- 移動端自適應布局

### 錯誤處理
- 完整的錯誤提示機制
- 後端連接狀態檢測
- 用戶友好的錯誤消息

## 開發指南

### 添加新路由
在 `App.jsx` 中添加新的導航按鈕和條件渲染

### 添加新功能
1. 在 `src/api.js` 中添加 API 調用方法
2. 在 `src/pages/` 中創建新的頁面組件
3. 在 `src/styles/` 中添加對應的 CSS 文件

## 常見問題

**Q: 如何連接不同的後端服務？**
A: 修改 `src/api.js` 中的 `API_BASE_URL` 或 `vite.config.js` 中的代理配置

**Q: 如何部署到生產環境？**
A: 運行 `npm run build`，將 `dist/` 目錄內容部署到靜態文件服務器

**Q: 支持哪些瀏覽器？**
A: 所有現代瀏覽器（Chrome、Firefox、Safari、Edge）

## 許可證

MIT
