# 📁 RedLens 数据工厂 - 项目结构

## 核心文件 (11个)

### 🔧 执行脚本 (4个)
```
fetch_fixtures.py              # 获取英超官方赛程
fetch_all_migu_videos.py      # 获取咪咕视频录像链接（支持历史翻页）
merge_data.py                  # 融合官方赛程与录像链接
update_all.sh                  # 一键自动化更新（推荐使用）
```

### 📄 配置文件 (3个)
```
requirements.txt               # Python依赖包列表
team_name_mapping.json         # 英超队名中英文翻译映射表
.gitignore                     # Git忽略规则
```

### 📊 数据文件 (3个)
```
matches.json                   # 英超官方赛程（38场，英文）
migu_videos_complete.json      # 咪咕视频数据（中文）
matches_with_videos.json       # 最终融合数据 ⭐ iOS App使用此文件
```

### 📖 文档 (2个)
```
prd.md                         # 产品需求文档
README_DataFactory.md          # 数据工厂使用指南
```

## 快速开始

```bash
# 1. 安装依赖
pip3 install -r requirements.txt
python3 -m playwright install chromium

# 2. 运行（推荐）
./update_all.sh

# 3. 获取结果
# iOS App 读取: matches_with_videos.json
```

## 文件大小参考

- matches.json: ~40KB (38场比赛)
- migu_videos_complete.json: ~20KB (22场，含录像链接)
- matches_with_videos.json: ~45KB (38场，融合数据) ⭐

## 更新频率

- 手动: 每周运行一次 `./update_all.sh`
- 自动: 添加到crontab `0 2 * * * /path/to/update_all.sh`

---
最后更新: 2026-01-08
