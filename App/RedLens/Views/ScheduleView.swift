import SwiftUI

struct ScheduleView: View {
    @AppStorage("showScores") private var showScores: Bool = true
    var allMatches: [Match]
    
    // 状态管理 (用于处理跳转和弹窗)
    @State private var showSpoilerAlert: Bool = false
    @State private var showNoVideoAlert: Bool = false
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
                                // 将每一行变成一个按钮
                                Button(action: {
                                    handleAction(for: match)
                                }) {
                                    ScheduleRow(match: match, showScore: showScores)
                                }
                                .buttonStyle(PlainButtonStyle()) // 去掉点击时的灰色背景闪烁
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
                    if let url = urlToOpen { openURL(url) }
                }, onCancel: { showSpoilerAlert = false })
                .zIndex(100)
            }
        }
        // 系统弹窗：无录像
        .alert("暂无视频源", isPresented: $showNoVideoAlert) {
            Button("知道了", role: .cancel) { }
        } message: {
            Text("本场比赛暂未收录直播或录像链接。")
        }
    }
    
    // 统一的处理逻辑 (和 HomeView 类似)
    func handleAction(for match: Match) {
        // 1. 无链接
        if !match.hasAction {
            self.showNoVideoAlert = true
            return
        }
        
        guard let url = URL(string: match.schemeUrl) else { return }
        
        // 2. 已完赛 -> 防剧透
        if match.status == "C" {
            self.urlToOpen = url
            withAnimation { self.showSpoilerAlert = true }
        } else {
            // 3. 未完赛 -> 直接跳直播
            openURL(url)
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
                
                // 赛事名 + 无录像标识
                VStack(alignment: .leading, spacing: 2) {
                    Text(match.competitionNameCN)
                        .font(.caption)
                        .foregroundColor(.gray)
                    
                    if !match.hasAction {
                        Text("暂无录像")
                            .font(.system(size: 8))
                            .padding(2)
                            .background(Color.gray.opacity(0.2))
                            .foregroundColor(.gray)
                            .cornerRadius(2)
                    }
                }
            }
            .frame(width: 60)
            
            // 右侧卡片
            HStack {
                Text(match.homeTeamNameCN)
                    .font(.body.bold())
                    .frame(maxWidth: .infinity, alignment: .trailing)
                    .lineLimit(1).minimumScaleFactor(0.8)
                    .foregroundColor(.black) // 确保按钮模式下文字是黑色的
                
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
            // 如果有链接，加一个淡淡的阴影表示可点击；如果没有，阴影淡一点
            .shadow(color: match.hasAction ? Color.arsenalRed.opacity(0.05) : Color.black.opacity(0.03), radius: 5, x: 0, y: 2)
        }
        .padding(.horizontal)
    }
    
    func formatDate(_ dateStr: String) -> String {
        let components = dateStr.split(separator: "-")
        if components.count >= 3 { return "\(components[1])-\(components[2])" }
        return dateStr
    }
}
