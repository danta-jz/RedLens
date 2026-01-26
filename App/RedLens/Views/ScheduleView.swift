import SwiftUI

struct ScheduleView: View {
    @AppStorage("showScores") private var showScores: Bool = true
    var allMatches: [Match]
    
    // 状态管理
    @State private var showSpoilerAlert: Bool = false
    @State private var urlToOpen: URL?
    
    @Environment(\.openURL) var openURL
    
    var body: some View {
        ZStack {
            // 底层：列表内容
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 16, pinnedViews: [.sectionHeaders]) {
                        Section(header:
                            HStack {
                                Spacer()
                                Toggle("显示比分", isOn: $showScores).labelsHidden()
                                Text(showScores ? "比分已显示" : "比分已隐藏").font(.caption).foregroundColor(.gray)
                                Spacer()
                            }.padding().background(Color.backgroundGray.opacity(0.95))
                        ) {
                            ForEach(allMatches) { match in
                                Button(action: {
                                    handleAction(for: match)
                                }) {
                                    ScheduleRow(match: match, showScore: showScores)
                                }
                                .buttonStyle(PlainButtonStyle())
                                .id(match.id)
                            }
                        }
                    }
                    .padding(.bottom, 20)
                }
                .background(Color.backgroundGray)
                .navigationTitle("全部赛程")
                .navigationBarTitleDisplayMode(.inline)
                .onAppear {
                    if let lastFinished = allMatches.last(where: { $0.status == "C" }) {
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                            withAnimation { proxy.scrollTo(lastFinished.id, anchor: .center) }
                        }
                    }
                }
            }
            
            // 顶层：防剧透弹窗
            if showSpoilerAlert {
                SpoilerAlertView(onConfirm: {
                    showSpoilerAlert = false
                    // 尝试跳转。如果URL为空，静默失败
                    if let url = urlToOpen { openURL(url) }
                }, onCancel: { showSpoilerAlert = false })
                .zIndex(100)
            }
        }
    }
    
    // 统一的处理逻辑 (与 HomeView 保持一致)
    func handleAction(for match: Match) {
        // 1. 如果已完赛，假装有链接，弹防剧透
        if match.status == "C" {
            self.urlToOpen = URL(string: match.schemeUrl)
            withAnimation { self.showSpoilerAlert = true }
        } else {
            // 2. 未完赛，尝试打开
            if let url = URL(string: match.schemeUrl) {
                openURL(url)
            }
        }
    }
}

struct ScheduleRow: View {
    let match: Match
    let showScore: Bool
    
    var body: some View {
        HStack(spacing: 15) {
            // 左侧
            VStack(alignment: .leading, spacing: 4) {
                Text(formatDate(match.bjDate))
                    .font(.system(.body, design: .monospaced).bold())
                    .foregroundColor(.black)
                
                // 赛事名 (删除了暂无录像的判断)
                Text(match.competitionNameCN)
                    .font(.caption)
                    .foregroundColor(.gray)
            }
            .frame(width: 60)
            
            // 右侧卡片
            HStack {
                Text(match.homeTeamNameCN)
                    .font(.body.bold())
                    .frame(maxWidth: .infinity, alignment: .trailing)
                    .lineLimit(1).minimumScaleFactor(0.8)
                    .foregroundColor(.black)
                
                ZStack {
                    if match.status == "C" {
                        Text(!showScore ? "VS" : (match.score.isEmpty ? "-" : match.score))
                            .font(.system(.title3, design: .monospaced).bold())
                            .foregroundColor(showScore ? .black : .gray)
                    } else {
                        Text(match.bjTime)
                            .font(.system(.body, design: .monospaced).bold())
                            .foregroundColor(.arsenalRed)
                    }
                }
                .frame(width: 70)
                .padding(.vertical, 6)
                .background(Color.backgroundGray)
                .cornerRadius(6)
                
                Text(match.awayTeamNameCN)
                    .font(.body.bold())
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .lineLimit(1).minimumScaleFactor(0.8)
                    .foregroundColor(.black)
            }
            .padding(.vertical, 16)
            .padding(.horizontal, 12)
            .background(Color.white)
            .cornerRadius(16)
            // 恢复所有阴影为可点击状态
            .shadow(color: Color.arsenalRed.opacity(0.05), radius: 5, x: 0, y: 2)
        }
        .padding(.horizontal)
    }
    
    func formatDate(_ dateStr: String) -> String {
        let components = dateStr.split(separator: "-")
        if components.count >= 3 { return "\(components[1])-\(components[2])" }
        return dateStr
    }
}
