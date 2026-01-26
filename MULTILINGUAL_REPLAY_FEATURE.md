# 多语言回放视频支持方案

**实现日期**: 2026-01-26  
**功能**: 在 App 上提供用户选择中文/粤语回放版本的功能

---

## 📊 功能概述

### 数据结构扩展

每场已完赛的比赛现在包含以下多语言字段：

```json
{
  "date": "2025-12-27",
  "opponent": "Brighton & Hove Albion",
  "migu_pid": "961573346",                    // 主 PID（默认中文优先）
  "migu_detail_url": "https://..../p/detail/961573346",
  
  // 新增：多语言版本 PID
  "migu_pid_mandarin": "961573346",           // 中文解说版本 PID
  "migu_detail_url_mandarin": "https://..../p/detail/961573346",
  "scheme_url_mandarin": "miguvideo://...",   // 中文版本深链接
  
  "migu_pid_cantonese": "961589182",          // 粤语解说版本 PID
  "migu_detail_url_cantonese": "https://..../p/detail/961589182",
  "scheme_url_cantonese": "miguvideo://...",  // 粤语版本深链接
  
  "migu_live_url": "https://..../p/live/..."  // 直播链接
}
```

---

## 🎯 使用场景

### iOS App 实现

```swift
// 1. 获取回放选项
let replays: [String] = []
if let mandarinPID = match.migu_pid_mandarin {
    replays.append("🇨🇳 中文解说")
}
if let cantonesePID = match.migu_pid_cantonese {
    replays.append("🇭🇰 粤语解说")
}

// 2. 根据用户选择跳转
if userSelectedLanguage == "mandarin" {
    // 使用 scheme_url_mandarin
    UIApplication.shared.open(URL(string: match.scheme_url_mandarin)!)
} else if userSelectedLanguage == "cantonese" {
    // 使用 scheme_url_cantonese
    UIApplication.shared.open(URL(string: match.scheme_url_cantonese)!)
} else {
    // 默认使用主版本
    UIApplication.shared.open(URL(string: match.scheme_url)!)
}
```

---

## 📈 数据统计

### 当前数据库

- **总比赛数**: 53 场
- **已完赛**: 24 场
- **有多语言版本**: 24 场（100%）
  - 含中文版本: 24 场
  - 含粤语版本: 3 场
  - 仅中文版本: 21 场

### 示例统计

| 比赛 | 日期 | 对手 | 中文PID | 粤语PID | 状态 |
|------|------|------|--------|--------|------|
| 阿森纳 vs 曼联 | 2025-08-17 | Manchester United | 957282050 | - | ✅ |
| 阿森纳 vs 布莱顿 | 2025-12-27 | Brighton | 961573346 | 961589182 | ✅ |
| ... | ... | ... | ... | ... | ... |

---

## 🔧 技术实现

### 1. 改进的 PID 筛选算法 (`fetch_all_migu_videos.py`)

新增 `fetch_full_match_replay()` 方法现在返回多语言 PID 字典：

```python
{
    'primary': 'PID',           # 优先级最高的 PID
    'mandarin': 'PID',          # 中文解说 PID
    'cantonese': 'PID',         # 粤语解说 PID
    'other': 'PID'              # 其他语言 PID
}
```

#### 核心算法

**优先级 1（最优）**: 中文3人解说 + 回放标签
- 解析括号识别解说人数
- 例: `全场回放（詹俊、张路、李子琪）` → 3人 → 优先级 13

**优先级 2**: 其他语言的回放标签视频

**优先级 3-5**: 兜底方案（长时间、官方格式等）

### 2. 数据合并 (`merge_data.py`)

合并时保留所有语言版本的 PID：

```python
# 合并官方赛程与咪咕数据
merged['migu_pid'] = migu.get('migu_pid')
merged['migu_pid_mandarin'] = migu.get('migu_pid_mandarin')
merged['migu_pid_cantonese'] = migu.get('migu_pid_cantonese')
```

### 3. 深链接生成 (`generate_deep_links.py`)

为每种语言版本生成独立的 Scheme URL：

```python
def _generate_vod_scheme(pid_value, mgdb_id=''):
    # 生成 miguvideo:// 深链接
    action_params = {
        "type": "JUMP_INNER_NEW_PAGE",
        "params": {
            "frameID": "default-frame",
            "pageID": "WORLDCUP_DETAIL",
            "location": "h5_share",
            "contentID": str(pid_value),
            "extra": {"mgdbID": str(mgdb_id)}
        }
    }
    # 返回 URL-encoded 的 JSON scheme
```

---

## 🚀 使用流程

### 1. 数据更新

```bash
cd DataFactory
python3 fetch_all_migu_videos.py    # 获取咪咕最新数据
python3 merge_data.py               # 合并官方赛程
python3 generate_deep_links.py      # 生成深链接
```

### 2. 数据检查

```bash
# 查看某场比赛的多语言信息
python3 << 'EOF'
import json
data = json.load(open('matches_with_videos.json'))
match = data[0]
print(f"主PID: {match.get('migu_pid')}")
print(f"中文: {match.get('migu_pid_mandarin')}")
print(f"粤语: {match.get('migu_pid_cantonese')}")
EOF
```

### 3. App 集成

```swift
// 在 HomeView 或回放列表中
if let cantonesePID = match.migu_pid_cantonese {
    Button(action: {
        // 打开粤语版本
    }) {
        Text("🇭🇰 粤语解说")
    }
}
```

---

## 📋 数据字段完整列表

### 录像相关字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `migu_pid` | 主PID（中文优先） | 961573346 |
| `migu_pid_mandarin` | 中文解说PID | 961573346 |
| `migu_pid_cantonese` | 粤语解说PID | 961589182 |
| `migu_pid_other` | 其他语言PID | - |
| `migu_detail_url` | 主详情页URL | https://www.miguvideo.com/p/detail/961573346 |
| `migu_detail_url_mandarin` | 中文版详情页 | https://www.miguvideo.com/p/detail/961573346 |
| `migu_detail_url_cantonese` | 粤语版详情页 | https://www.miguvideo.com/p/detail/961589182 |

### 深链接字段

| 字段 | 说明 | 类型 |
|------|------|------|
| `scheme_url` | 主Scheme URL | miguvideo:// |
| `scheme_url_mandarin` | 中文Scheme URL | miguvideo:// |
| `scheme_url_cantonese` | 粤语Scheme URL | miguvideo:// |

### 直播相关字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `migu_live_url` | 直播链接 | https://www.miguvideo.com/p/live/120000542300 |

---

## ✅ 验证检查表

- [x] 支持返回多语言 PID
- [x] 中文3人解说优先级最高（已验证：詹俊、张路、李子琪）
- [x] 粤语解说正确识别（已验证：陈凯冬、何辉）
- [x] 生成语言特定的深链接
- [x] 数据合并保留多语言信息
- [x] 输出格式包含所有语言版本

---

## 📞 注意事项

1. **主PID选择**：如无特殊指定，使用 `migu_pid`（中文优先）
2. **粤语可用性**：并非所有比赛都有粤语版本，需检查 `migu_pid_cantonese` 是否为空
3. **向后兼容**：原有的 `migu_pid` 字段保持不变，新增字段不影响旧版本
4. **时间成本**：多语言筛选会增加爬虫运行时间，首次运行约为原来的 1.5-2 倍

---

## 🔄 后续优化方向

1. **自动识别其他语言** - 英文解说、体育评论版本等
2. **用户偏好保存** - 记住用户选择的语言偏好
3. **语音说明** - 自动识别解说员并在 App 中显示解说阵容
4. **质量评分** - 根据时长和类型自动评分（5星系统）


