# 🔴 RedLens：产品需求文档 (PRD) & 技术架构方案

> **Version:** 1.2 (Updated: 2026-01-08)
> **Owner:** PM (RedLens)

## 1. 产品愿景 (Product Vision)
RedLens 是一款专为阿森纳（Arsenal）死忠球迷打造的**“反剧透”赛程与回看工具**。
它的核心价值是**“纯净”**：在用户观看录像之前，彻底屏蔽一切比分、新闻和评论，将被剧透的风险降为零。

* **核心隐喻**：手术刀（Surgical Knife）。精准切除剧透毒瘤，只保留比赛本身。
* **设计原则**：启动即用，用完即走。没有登录，没有社交，没有设置。

---

## 2. 功能需求 (Functional Requirements)

### 2.1 首页：赛程列表 (The Timeline)
* **展示逻辑**：
    * **过去 (Past)**：已结束的比赛。**严禁显示比分**。点击直接进入“回看模式”。
    * **未来 (Future)**：未开始的比赛。显示北京时间、对手、主客场信息。
    * **高亮 (Focus)**：最近的一场比赛（无论是刚结束等待回看，还是即将开始）必须在视觉上通过“红色呼吸态”或其他方式强调。
* **交互**：
    * 下拉刷新（触发数据重新加载）。
    * 点击 Past 比赛 -> 跳转播放器。

### 2.2 核心页：无剧透播放器 (The Safe Room)
这是产品的灵魂。它本质上是一个浏览器，但对咪咕视频 PC 网页版进行了“外科手术”。

* **加载逻辑**：
    * 自动跳转到该场比赛的 **纯净录像页** (`/p/detail/xxxx`)，而非直播间页。
    * **强制伪装**：模拟桌面端（Mac/Windows）访问，绕过“下载 App”的强制引导。
* **净化逻辑 (The Purge)**：
    * **视觉屏蔽**：在画面加载出来的 0.1 秒内，利用代码强制隐藏网页上的比分条、相关新闻推荐、评论区。
    * **全屏锁定**：尽可能直接提取视频流全屏播放，或者让用户聚焦在视频窗口，忽略周围噪音。

---

## 3. 技术架构方案 (Technical Architecture)
我们采用 “前后端分离，以 GitHub 为中枢” 的极简架构。

### 3.1 模块一：数据工厂 (Data Factory Agent) **[核心更新]**
* **角色**：后端 ETL / 数据融合引擎。
* **技术栈**：Python + Playwright + Tenacity。
* **核心工作流**：采用“双源融合”策略，即 **官方赛程骨架 + 咪咕视频血肉**。

#### **Step 1: 建立骨架 (Base Schedule Fetching)**
* **数据源**：Sky Sports 或 Premier League 官网。
* **目的**：获取最准确的比赛时间、标准化的对手名称（英文）、场馆信息。
* **输出**：基础 `Match` 对象列表（此时 `migu_url` 为空）。

#### **Step 2: 获取视频源 (Video Source Discovery)**
* **策略**：**咪咕直连穿透 (Migu Direct Penetration)**。直接从咪咕源头抓取。
* **抓取路径**：
    1.  **扫描列表 (Scan)**：访问咪咕英超赛程页 (`/p/schedule/5`)，找到阿森纳已完赛的场次，获取其跳转链接（通常是含剧透的 Live 房间链接 `/p/live/xxxx`）。
    2.  **提取 PID (Extraction)**：
        * 提取 **`pid`** (Content ID，例如 `962119740`)。
    3.  **清洗 URL**：将 PID 拼装为无杂质的详情页 URL：`https://www.miguvideo.com/p/detail/{PID}`。

#### **Step 3: 数据融合 (Data Association)**
* **逻辑**：将 Step 2 抓取到的视频 URL，通过 **“日期 + 对手”** 的匹配算法，挂载到 Step 1 的基础赛程上。
* **产出**：生成最终的 `matches.json`，确保每场已结束的比赛都有一个准确的 `migu_url`。

#### **Step 4: 分发 (Delivery)**
* 通过 Git Push 更新 GitHub 仓库，供 iOS 端拉取。

### 3.2 模块二：iOS 客户端 (The Shell)
* **角色**：前端展示。
* **技术栈**：Swift 5 + SwiftUI。
* **数据源**：直接读取本地 Bundle 的 JSON（MVP阶段），或从 GitHub Raw URL 拉取（联网阶段）。
* **核心类**：
    * `Match`: 数据模型，对应 JSON 结构，新增 `migu_url` 字段 (Optional)。
    * `MatchListView`: 极简列表渲染。

### 3.3 模块三：净化引擎 (The Lens Engine)
* **角色**：核心业务逻辑实现。
* **技术栈**：WKWebView + JavaScript Injection (UserScript)。
* **关键技术点**：
    * **User-Agent Spoofing**：欺骗咪咕服务器以为我们在用电脑访问。
    * **CSS Injection (样式手术)**：
        * 编写一段 CSS，将 `.score-bar`, `.news-feed`, `.comments` 以及 **视频下方的带比分标题** (`.video-title`) 设为 `display: none !important`。
        * **策略**：在网页加载开始时立即注入，防止剧透闪烁。
    * **DOM Cleaning (结构手术)**：使用 JS 移除多余的广告节点。

---

## 4. MVP 阶段验证标准 (Definition of Done)
1.  **赛程准确**：App 赛程时间与英超官网一致。
2.  **链接纯净**：`matches.json` 中已结束比赛的 `migu_url` 必须是 `/p/detail/` 格式，而非 `/p/live/`。
3.  **播放成功**：手机点击列表，能直接唤起咪咕播放器并在手机上播放。
4.  **零剧透**：从列表点击到视频开始播放的全过程，用户无法看到任何比分数字（包括视频标题）。
