# RedLens 数据工厂 - 使用说明

## 📦 模块一：赛程数据抓取器

### 功能概述
自动从英超官网或阿森纳官网抓取最新赛程数据，为 RedLens App 提供结构化的比赛信息。

### 核心特性
- ✅ **多数据源智能回退**：优先使用英超官网 API，失败时自动切换至阿森纳官网
- ✅ **自动重试机制**：网络波动时最多重试 3 次，指数退避策略
- ✅ **幂等性设计**：多次运行结果一致，确保数据完整性
- ✅ **时区自动转换**：统一转换为北京时间 (UTC+8)
- ✅ **详细日志输出**：实时监控抓取进度

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 安装 Python 依赖库
pip install -r requirements.txt

# 安装 Playwright 浏览器驱动（首次运行必需）
playwright install chromium
```

### 2. 运行脚本

```bash
python fetch_fixtures.py
```

### 3. 查看结果

脚本执行后会生成 `matches.json` 文件，格式如下：

```json
[
  {
    "date": "2026-01-11",
    "time": "23:00",
    "opponent": "Tottenham Hotspur",
    "is_home": true,
    "venue": "Emirates Stadium"
  },
  {
    "date": "2026-01-18",
    "time": "20:30",
    "opponent": "Manchester City",
    "is_home": false,
    "venue": "Etihad Stadium"
  }
]
```

---

## 📊 数据字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `date` | string | 比赛日期 (YYYY-MM-DD) | "2026-01-11" |
| `time` | string | 比赛时间 (HH:MM，北京时间) | "23:00" |
| `opponent` | string | 对手球队名称 | "Tottenham Hotspur" |
| `is_home` | boolean | 是否为主场比赛 | true / false |
| `venue` | string | 比赛场馆 | "Emirates Stadium" |

---

## 🔧 配置说明

所有配置项位于 `fetch_fixtures.py` 的顶部：

```python
OUTPUT_FILE = "matches.json"          # 输出文件名
ARSENAL_TEAM_ID = 1                   # 阿森纳在英超官网的球队 ID
TIMEOUT_MS = 30000                    # 请求超时时间 (毫秒)
TARGET_TIMEZONE = 'Asia/Shanghai'     # 目标时区 (北京时间)
```

如需修改，直接编辑这些常量即可。

---

## 🛠️ 故障排查

### 问题 1：playwright 安装失败
**症状**：提示 `playwright: command not found`

**解决方案**：
```bash
# Windows
python -m playwright install chromium

# macOS/Linux
python3 -m playwright install chromium
```

### 问题 2：所有数据源均失败
**症状**：日志显示 `❌ 所有数据源均不可用`

**可能原因**：
1. 网络连接问题 → 检查网络或使用代理
2. 网站结构变更 → 联系开发者更新选择器
3. 反爬限制 → 增加请求间隔或更换 IP

### 问题 3：时区转换错误
**症状**：比赛时间不对

**解决方案**：
修改 `TARGET_TIMEZONE` 配置：
```python
# 东八区 (北京/上海)
TARGET_TIMEZONE = pytz.timezone('Asia/Shanghai')

# 其他时区
TARGET_TIMEZONE = pytz.timezone('America/New_York')  # 纽约
TARGET_TIMEZONE = pytz.timezone('Europe/Paris')      # 巴黎
```

---

## 🎯 设计哲学（致敬张小龙）

### 1. 极简主义
- **单一职责**：脚本只做一件事 —— 抓取赛程数据
- **零配置运行**：开箱即用，无需复杂设置
- **静默执行**：后台完成任务，不打扰用户

### 2. 本质主义
- **多余元素零容忍**：只保留必需的字段
- **直觉优先**：数据结构清晰，一目了然
- **工具属性**：完成任务即退出，不留痕迹

### 3. 生产级别
- **鲁棒性**：多重容错机制，确保在网络波动下仍能运行
- **可维护性**：详细注释 + 模块化设计
- **可扩展性**：轻松添加新数据源（如欧冠、足总杯）

---

## 📝 后续扩展

### 未来可能添加的功能：
- [ ] 支持多球队赛程抓取
- [ ] 增加赛果数据（score, status）
- [ ] 定时任务自动更新
- [ ] Webhook 通知（赛程变动时推送）
- [ ] 数据库存储（替代 JSON）

---

## 📄 许可证
MIT License - RedLens Project

**作者**：RedLens CTO (AI Architect)  
**项目哲学**：Less is More | 用户体验至上
