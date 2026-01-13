# 📱 RedLens iOS 集成指南

## Deep Link 使用说明

### 数据源

iOS App 使用 `matches_with_videos.json` 文件，其中每场比赛包含以下关键字段：

```json
{
  "date": "2026-01-04",
  "time": "01:30",
  "opponent": "Bournemouth",
  "is_home": false,
  "venue": "Vitality Stadium",
  "status": "C",
  "arsenal_score": 3.0,
  "opponent_score": 2.0,
  "outcome": "A",
  "migu_pid": "962119740",
  "migu_detail_url": "https://www.miguvideo.com/p/detail/962119740",
  "migu_live_url": "https://www.miguvideo.com/p/live/120000542331",
  "scheme_url": "miguvideo://miguvideo?action=%7B%22type%22%3A%20%22JUMP_INNER_NEW_PAGE%22..."
}
```

### Swift 集成示例

#### 1. 数据模型

```swift
struct Match: Codable {
    let date: String
    let time: String
    let opponent: String
    let isHome: Bool
    let venue: String
    let status: String
    
    // 可选字段 - 已完赛比赛才有
    let arsenalScore: Double?
    let opponentScore: Double?
    let outcome: String?
    let miguPid: String?
    let miguDetailUrl: String?
    let miguLiveUrl: String?
    let schemeUrl: String?  // ⭐ Deep Link
    
    enum CodingKeys: String, CodingKey {
        case date, time, opponent, venue, status, outcome
        case isHome = "is_home"
        case arsenalScore = "arsenal_score"
        case opponentScore = "opponent_score"
        case miguPid = "migu_pid"
        case miguDetailUrl = "migu_detail_url"
        case miguLiveUrl = "migu_live_url"
        case schemeUrl = "scheme_url"
    }
}
```

#### 2. 加载数据

```swift
func loadMatches() -> [Match] {
    guard let url = Bundle.main.url(forResource: "matches_with_videos", withExtension: "json"),
          let data = try? Data(contentsOf: url),
          let matches = try? JSONDecoder().decode([Match].self, from: data) else {
        return []
    }
    return matches
}
```

#### 3. 打开咪咕视频 App

```swift
func openMiguVideo(match: Match) {
    // 检查是否有 Deep Link
    guard let schemeUrl = match.schemeUrl,
          let url = URL(string: schemeUrl) else {
        // 没有录像，显示提示
        showAlert(message: "该场比赛暂无录像")
        return
    }
    
    // 检查是否安装了咪咕视频
    if UIApplication.shared.canOpenURL(url) {
        // 打开咪咕视频 App
        UIApplication.shared.open(url) { success in
            if !success {
                // 打开失败，提示用户安装咪咕视频
                self.showInstallMiguAlert()
            }
        }
    } else {
        // 未安装咪咕视频，引导用户安装
        showInstallMiguAlert()
    }
}

func showInstallMiguAlert() {
    let alert = UIAlertController(
        title: "需要安装咪咕视频",
        message: "请先安装咪咕视频App才能观看比赛回放",
        preferredStyle: .alert
    )
    
    alert.addAction(UIAlertAction(title: "去安装", style: .default) { _ in
        // 跳转到 App Store
        if let url = URL(string: "https://apps.apple.com/cn/app/咪咕视频/id1234567890") {
            UIApplication.shared.open(url)
        }
    })
    
    alert.addAction(UIAlertAction(title: "取消", style: .cancel))
    
    present(alert, animated: true)
}
```

#### 4. SwiftUI 示例

```swift
struct MatchRow: View {
    let match: Match
    
    var body: some View {
        Button(action: {
            openMiguVideo(match: match)
        }) {
            HStack {
                VStack(alignment: .leading) {
                    Text(match.opponent)
                        .font(.headline)
                    Text("\(match.date) \(match.time)")
                        .font(.caption)
                        .foregroundColor(.gray)
                }
                
                Spacer()
                
                if match.schemeUrl != nil {
                    Image(systemName: "play.circle.fill")
                        .foregroundColor(.red)
                }
            }
        }
        .disabled(match.schemeUrl == nil)  // 未完赛的比赛禁用
    }
}
```

### 注意事项

1. **空值检查**: 未来的比赛没有 `scheme_url`，需要做空值检查
2. **反剧透**: 已完赛的比赛在列表中不要显示比分，只在播放器中显示
3. **App 检测**: 使用 `canOpenURL` 检查用户是否安装了咪咕视频
4. **Info.plist 配置**: 需要在 `LSApplicationQueriesSchemes` 中添加 `miguvideo`

```xml
<key>LSApplicationQueriesSchemes</key>
<array>
    <string>miguvideo</string>
</array>
```

### 测试工具

使用 Python 测试工具验证 Deep Link：

```bash
# 查看所有比赛
python3 test_deep_link.py

# 查看指定日期的比赛
python3 test_deep_link.py 2026-01-04
```

### 数据更新

数据工厂每次运行都会自动生成最新的 Deep Link，iOS App 只需要：

1. 定期拉取最新的 `matches_with_videos.json`
2. 或者在 App 启动时检查更新
3. 或者使用 GitHub Actions 自动推送更新

---

更多信息请参考 `README_DataFactory.md`

