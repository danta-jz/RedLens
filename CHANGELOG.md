# 🔴 RedLens 数据工厂 - 更新日志

## 2026-01-13 - Deep Link 支持

### ✨ 新增功能

1. **Deep Link 生成器** (`generate_deep_links.py`)
   - 为每场比赛生成咪咕视频App的Deep Link
   - 自动提取 `mgdbID`（房间号）和 `contentID`（录像ID）
   - 生成标准格式的 Scheme URL
   - 支持从iOS App直接唤起咪咕视频App播放

2. **全场回放PID修复**
   - 修复了之前获取的是集锦PID的问题
   - 现在正确获取全场回放PID（2-3小时时长）
   - 从 `replayList` 中提取数据而不是 `recommendList`
   - 使用时长排序选择最长的视频（全场回放）

3. **Live URL 修复**
   - 使用正确的 `mgdbID` 而不是 `roomId`
   - URL格式：`https://www.miguvideo.com/p/live/120000xxxxxx`

### 📝 更新内容

- 更新了 `update_all.sh`，添加第4步：生成Deep Link
- 更新了 `README_DataFactory.md`，添加Deep Link说明
- 新增 `README_iOS_Integration.md`，提供iOS集成指南
- 新增 `test_deep_link.py`，用于测试和验证Deep Link
- 更新了 `PROJECT_STRUCTURE.md`

### 🎯 数据字段

`matches_with_videos.json` 新增字段：

```json
{
  "scheme_url": "miguvideo://miguvideo?action=%7B%22type%22%3A%20%22JUMP_INNER_NEW_PAGE%22..."
}
```

### 📊 数据统计

- 总比赛数：38场
- 已完赛：21场
- 有全场回放：21场
- 有Deep Link：21场
- 覆盖率：100%

### 🔧 技术细节

**Deep Link 格式：**
```
miguvideo://miguvideo?action={URL_ENCODED_JSON}
```

**JSON 载荷：**
```json
{
  "type": "JUMP_INNER_NEW_PAGE",
  "params": {
    "frameID": "default-frame",
    "pageID": "WORLDCUP_DETAIL",
    "location": "h5_share",
    "contentID": "962119740",
    "extra": {
      "mgdbID": "120000542331"
    }
  }
}
```

---

## 2026-01-08 - 初始版本

### ✨ 核心功能

1. **官方赛程抓取** (`fetch_fixtures.py`)
   - 从英超官网API获取2025/26赛季所有38场比赛
   - 包含比分、结果、场馆信息
   - 自动转换为北京时间

2. **咪咕视频抓取** (`fetch_all_migu_videos.py`)
   - 获取所有阿森纳比赛的录像链接
   - 支持历史和未来比赛
   - 自动去重

3. **数据融合** (`merge_data.py`)
   - 融合官方赛程和咪咕视频数据
   - 支持中英文队名翻译
   - 生成最终JSON文件

4. **一键更新** (`update_all.sh`)
   - 自动运行所有脚本
   - 支持cron定时任务

