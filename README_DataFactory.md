# 🏭 RedLens 数据工厂使用指南

## 📋 概述

RedLens 数据工厂负责获取阿森纳 2025/26 赛季的完整赛程数据和咪咕视频录像链接，并将两者融合成一个完整的数据集。

## 🎯 核心功能

1. **官方赛程获取** - 从英超官网获取准确的比赛时间、对手、场馆信息
2. **录像链接获取** - 从咪咕视频获取已完赛比赛的录像 PID 和无剧透播放链接
3. **数据融合** - 将官方赛程与录像链接匹配，生成最终数据

## 📦 依赖安装

```bash
pip3 install --user playwright pytz tenacity aiohttp
python3 -m playwright install chromium
```

## 🚀 快速开始

### 方式1：一键运行（推荐）

```bash
./update_all.sh
```

这个脚本会依次执行：
1. 获取英超官方赛程
2. 获取咪咕视频录像
3. 融合数据

### 方式2：分步执行

```bash
# Step 1: 获取官方赛程
python3 fetch_fixtures.py

# Step 2: 获取咪咕视频
python3 fetch_all_migu_videos.py

# Step 3: 融合数据
python3 merge_data.py
```

## 📁 输出文件

| 文件名 | 说明 | 用途 |
|--------|------|------|
| `matches.json` | 英超官方赛程数据 | 包含所有38场比赛的详细信息（英文） |
| `migu_videos_complete.json` | 咪咕视频数据 | 包含录像PID和播放链接（中文） |
| `matches_with_videos.json` | **最终融合数据** | iOS App 使用的完整数据 |
| `team_name_mapping.json` | 队名翻译映射表 | 中英文队名对照 |

## 📊 数据结构

### matches_with_videos.json（最终数据）

```json
[
  {
    "date": "2025-08-17",
    "time": "23:30",
    "opponent": "Manchester United",
    "is_home": false,
    "venue": "Old Trafford",
    "status": "C",
    "arsenal_score": 1,
    "opponent_score": 0,
    "outcome": "A",
    "migu_pid": "957281860",
    "migu_detail_url": "https://www.miguvideo.com/p/detail/957281860",
    "migu_live_url": "https://www.miguvideo.com/p/live/room..."
  }
]
```

### 字段说明

- `date`: 比赛日期（北京时间）
- `time`: 比赛时间（北京时间）
- `opponent`: 对手名称（英文）
- `is_home`: 是否主场（true/false）
- `venue`: 场馆名称
- `status`: 比赛状态（`C`=已完赛，`U`=未开始）
- `arsenal_score`: 阿森纳得分（已完赛时存在）
- `opponent_score`: 对手得分（已完赛时存在）
- `outcome`: 比赛结果（`H`=主场胜，`A`=客场胜，`D`=平局）
- `migu_pid`: 咪咕视频Content ID（已完赛时存在）
- `migu_detail_url`: **纯净录像页面**（无剧透，推荐使用！）
- `migu_live_url`: 直播间页面（使用mgdbId，格式: `/p/live/120000xxxxxx`）
- `scheme_url`: **咪咕视频App Deep Link**（用于从其他App唤起咪咕视频App播放）

## 🔄 定期更新

### 使用 cron 自动化（推荐）

每天凌晨2点自动更新：

```bash
crontab -e

# 添加以下行
0 2 * * * /path/to/RedLens/update_all.sh >> /path/to/RedLens/update.log 2>&1
```

### 手动更新

建议在以下时间点手动运行：
- ✅ 比赛结束后（第二天）- 获取新的录像链接
- ✅ 每周一次 - 保持数据最新

## 🎬 关键发现

### ✨ 咪咕 detail 页面无剧透！

经过验证，咪咕的 `/p/detail/{pid}` 页面**本身就不包含比分信息**，这意味着：

- ✅ MVP 阶段无需实现复杂的剧透屏蔽逻辑
- ✅ 可以直接在 iOS App 中加载这个 URL
- ✅ 用户从列表点击到播放全程零剧透

### 📡 咪咕 API 规律

- **当前/未来**: `/normal-match-list/0/5/default/1/miguvideo`
- **历史翻页**: `/normal-match-list/{日期}/5/up/1/miguvideo`
- 每次API返回约一周的比赛数据
- 需要多次请求才能覆盖整个赛季

## 🔧 核心脚本说明

### 1. fetch_fixtures.py

从英超官网 API 获取官方赛程。

**数据源**: `https://footballapi.pulselive.com/football/fixtures`

**特点**:
- ✅ 数据权威准确
- ✅ 包含比分和结果
- ✅ 时间自动转换为北京时间
- ✅ 支持重试机制

### 2. fetch_all_migu_videos.py

从咪咕视频获取所有阿森纳比赛的录像链接（全场回放）。

**抓取策略**:
1. 从当前日期开始往前翻页（up 方向）
2. 每次获取约一周的数据
3. 持续翻页直到赛季开始
4. 同时获取未来比赛（default 模式）

**输出**: 每场已完赛比赛的 PID 和 detail URL

### 3. merge_data.py

将官方赛程与咪咕录像链接融合。

**匹配策略**:
- 日期匹配
- 对手名称匹配（支持中英文翻译）
- 使用 `team_name_mapping.json` 进行名称转换

### 4. generate_deep_links.py

为每场比赛生成咪咕视频App的Deep Link。

**功能**:
- 从 `migu_live_url` 提取 `mgdbID`（房间号）
- 结合 `migu_pid`（内容ID）生成标准格式的 Scheme URL
- 生成的 Deep Link 可用于从其他App唤起咪咕视频App并直接播放

**Deep Link 格式**:
```
miguvideo://miguvideo?action={URL_ENCODED_JSON}
```

其中 JSON 载荷结构为：
```json
{
  "type": "JUMP_INNER_NEW_PAGE",
  "params": {
    "frameID": "default-frame",
    "pageID": "WORLDCUP_DETAIL",
    "location": "h5_share",
    "contentID": "录像ID",
    "extra": {
      "mgdbID": "房间号"
    }
  }
}
```

## 📈 当前数据状态

```
📊 2025/26 赛季统计（截至 2026-01-08）:
   总场次: 38 场
   已完赛: 20 场（100% 有录像）
   未完赛: 18 场
   战绩: 17胜 3平 0负
   积分: 54 分
```

## 🐛 故障排查

### 问题1: 获取官方赛程失败

```bash
❌ 英超官网抓取失败: net::ERR_CONNECTION_CLOSED
```

**解决方案**: 检查网络连接，或稍后重试

### 问题2: 咪咕API返回411错误

这是正常的，表示已经到达数据边界。脚本会自动停止。

### 问题3: 数据融合匹配失败

检查 `team_name_mapping.json` 是否包含所有对手的中英文对照。

## 📝 TODO

- [ ] 支持其他赛事（欧冠、足总杯等）
- [ ] 添加数据验证和完整性检查
- [ ] 支持增量更新（只更新新比赛）
- [ ] 添加通知功能（新录像可用时推送）

## 📞 技术支持

如有问题，请查看日志文件或提交 Issue。

---

**最后更新**: 2026-01-08
**版本**: v1.0
