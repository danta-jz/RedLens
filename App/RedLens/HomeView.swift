import SwiftUI

struct HomeView: View {
    @ObservedObject var store: MatchStore
    
    @State private var selectedTab: Int = 1
    
    // 状态管理
    @State private var showSpoilerAlert: Bool = false
    @State private var showNoVideoAlert: Bool = false // 新增：无录像提示
    @State private var urlToOpen: URL?
    
    @Environment(\.openURL) var openURL
    
    var body: some View {
        ZStack {
            Color.backgroundGray.ignoresSafeArea()
            
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    // Header
                    HStack {
                        Text("RedLens")
                            .font(.system(size: 28, weight: .heavy))
                            .foregroundColor(.black)
                        Spacer()
                        NavigationLink(destination: ScheduleView(allMatches: store.matches)) {
                            Image(systemName: "calendar")
                                .font(.title2)
                                .foregroundColor(.black)
                                .padding(10)
                                .background(Color.white)
                                .clipShape(Circle())
                                .shadow(color: .black.opacity(0.1), radius: 3)
                        }
                    }
                    .padding(.horizontal)
                    .padding(.top, 10)
                    
                    heroCardSection
                    
                    HStack {
                        Text("后续赛程")
                            .font(.title3.bold())
                            .foregroundColor(.black)
                        Spacer()
                        NavigationLink(destination: ScheduleView(allMatches: store.matches)) {
                            Text("查看全部").font(.subheadline).foregroundColor(.arsenalRed)
                        }
                    }
                    .padding(.horizontal)
                    
                    LazyVStack(spacing: 12) {
                        ForEach(store.futureMatches) { match in
                            MatchListRow(match: match)
                        }
                    }
                    .padding(.horizontal)
                    
                    Spacer(minLength: 50)
                }
            }
            .navigationBarHidden(true)
            
            // --- 全局覆盖层：防剧透弹窗 ---
            if showSpoilerAlert {
                SpoilerAlertView(onConfirm: {
                    showSpoilerAlert = false
                    if let url = urlToOpen { openURL(url) }
                }, onCancel: { showSpoilerAlert = false })
                .zIndex(100)
            }
        }
        // --- 系统弹窗：无录像提示 ---
        .alert("暂无视频源", isPresented: $showNoVideoAlert) {
            Button("知道了", role: .cancel) { }
        } message: {
            Text("本场比赛暂未收录直播或录像链接。\n(如：联赛杯/欧冠/友谊赛等)")
        }
        .onAppear { setupSmartDefaults() }
    }
    
    var heroCardSection: some View {
        VStack(spacing: 0) {
            TabView(selection: $selectedTab) {
                if let past = store.lastFinishedMatch {
                    HeroMatchCard(match: past, isPast: true) { handleAction(for: past) }
                        .tag(0).padding(.horizontal)
                } else {
                    Text("新赛季即将开始").tag(0)
                }
                
                if let next = store.nextMatch {
                    HeroMatchCard(match: next, isPast: false) { handleAction(for: next) }
                        .tag(1).padding(.horizontal)
                } else {
                    Text("本赛季已结束").tag(1)
                }
            }
            .tabViewStyle(PageTabViewStyle(indexDisplayMode: .never))
            .frame(height: 380)
        }
    }
    
    func setupSmartDefaults() { selectedTab = store.defaultHomeTab }
    
    // 统一处理点击逻辑
    func handleAction(for match: Match) {
        // 1. 如果没有链接，直接弹提示
        if !match.hasAction {
            self.showNoVideoAlert = true
            return
        }
        
        guard let url = URL(string: match.schemeUrl) else { return }
        
        // 2. 如果已完赛，先弹防剧透
        if match.status == "C" {
            self.urlToOpen = url
            withAnimation { self.showSpoilerAlert = true }
        } else {
            // 3. 直播直接跳
            openURL(url)
        }
    }
}

// MARK: - 大卡片 (支持"暂无录像"状态)
struct HeroMatchCard: View {
    let match: Match
    let isPast: Bool
    let action: () -> Void
    
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 24).fill(Color.darkCardBg)
            VStack {
                HStack {
                    // 左上角标签逻辑
                    if !match.hasAction {
                        // 无链接状态
                        Label("暂无录像", systemImage: "video.slash.fill")
                            .font(.caption.bold())
                            .padding(.horizontal, 10).padding(.vertical, 6)
                            .background(Color.white.opacity(0.1)) // 灰色背景
                            .foregroundColor(.gray)
                            .cornerRadius(8)
                    } else if isPast {
                        // 有录像
                        Label("全场回放", systemImage: "play.circle.fill")
                            .font(.caption.bold())
                            .padding(.horizontal, 10).padding(.vertical, 6)
                            .background(Color.arsenalRed).foregroundColor(.white).cornerRadius(8)
                    } else {
                        // 直播
                        Label("即将开始", systemImage: "timer")
                            .font(.caption.bold())
                            .padding(.horizontal, 10).padding(.vertical, 6)
                            .background(Color.gray.opacity(0.3)).foregroundColor(.white).cornerRadius(8)
                    }
                    
                    Spacer()
                    
                    Text("\(formatDateShort(match.bjDate)) \(match.bjTime)")
                        .font(.caption.bold())
                        .foregroundColor(.white.opacity(0.8))
                        .padding(6)
                        .background(Color.white.opacity(0.1))
                        .cornerRadius(4)
                }
                .padding([.top, .horizontal], 20)
                
                Spacer()
                
                // 中间对阵
                HStack(alignment: .center, spacing: 0) {
                    Text(match.homeTeamNameCN)
                        .font(.system(size: 28, weight: .heavy))
                        .foregroundColor(.white)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: .infinity)
                    
                    VStack(spacing: 4) {
                        Text("VS")
                            .font(.system(size: 24, weight: .black).italic())
                            .foregroundColor(.white.opacity(0.3))
                        Text(match.isHome ? "主场" : "客场")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundColor(.white.opacity(0.6))
                            .padding(.horizontal, 6).padding(.vertical, 2)
                            .background(Color.white.opacity(0.1)).cornerRadius(4)
                    }
                    .frame(width: 60)
                    
                    Text(match.awayTeamNameCN)
                        .font(.system(size: 28, weight: .heavy))
                        .foregroundColor(.white)
                        .multilineTextAlignment(.center)
                        .frame(maxWidth: .infinity)
                }
                .padding(.horizontal, 10)
                
                Spacer()
                
                // 底部按钮
                Button(action: action) {
                    HStack {
                        VStack(alignment: .leading) {
                            if !match.hasAction {
                                Text("NO VIDEO AVAILABLE").font(.system(size: 10, weight: .bold)).opacity(0.6)
                                Text("暂无视频源").font(.title3.bold()).opacity(0.6)
                            } else {
                                Text(isPast ? "FULL MATCH REPLAY" : "LIVE BROADCAST")
                                    .font(.system(size: 10, weight: .bold)).opacity(0.8)
                                Text(isPast ? "点击播放 · 无剧透" : "进入直播间")
                                    .font(.title3.bold())
                            }
                        }
                        Spacer()
                        if match.hasAction {
                            Image(systemName: "arrow.right").font(.title2)
                        }
                    }
                    .foregroundColor(.white).padding()
                    .background(
                        // 如果没链接，按钮变灰
                        match.hasAction ?
                        LinearGradient(gradient: Gradient(colors: [Color.arsenalRed, Color.arsenalRed.opacity(0.8)]), startPoint: .leading, endPoint: .trailing) :
                        LinearGradient(gradient: Gradient(colors: [Color.gray.opacity(0.3), Color.gray.opacity(0.3)]), startPoint: .leading, endPoint: .trailing)
                    )
                    .cornerRadius(16)
                }
                .padding(20)
                .disabled(false) // 保持按钮可点，为了弹出"无视频"提示
            }
        }
        .shadow(color: Color.black.opacity(0.1), radius: 10, x: 0, y: 5)
    }
    
    func formatDateShort(_ dateStr: String) -> String {
        let components = dateStr.split(separator: "-")
        return components.count >= 3 ? "\(components[1])-\(components[2])" : dateStr
    }
}

// 列表行保持不变
struct MatchListRow: View {
    let match: Match
    var body: some View {
        HStack {
            VStack(alignment: .center, spacing: 2) {
                Text(formatMonth(match.bjDate)).font(.caption).foregroundColor(.gray)
                Text(formatDay(match.bjDate)).font(.title2.bold()).foregroundColor(.black)
            }
            .frame(width: 45)
            Divider().frame(height: 30)
            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 8) {
                    Text(match.isHome ? match.awayTeamNameCN : match.homeTeamNameCN).font(.headline).foregroundColor(.black)
                    if match.isFinished { Text(match.score).font(.subheadline.monospaced().bold()).foregroundColor(.gray) }
                }
                HStack {
                    Text(match.competitionNameCN).font(.caption).foregroundColor(.gray)
                    Text(match.bjTime).font(.caption).foregroundColor(.arsenalRed)
                }
            }
            Spacer()
            Text(match.isHome ? "主场" : "客场").font(.caption.bold()).padding(.horizontal, 8).padding(.vertical, 4).background(Color.gray.opacity(0.1)).foregroundColor(.gray).cornerRadius(4)
        }
        .padding().background(Color.white).cornerRadius(16).shadow(color: Color.black.opacity(0.03), radius: 5, x: 0, y: 2)
    }
    func formatMonth(_ dateStr: String) -> String { let c = dateStr.split(separator: "-"); return c.count > 1 ? "\(c[1])月" : "" }
    func formatDay(_ dateStr: String) -> String { let c = dateStr.split(separator: "-"); return c.count > 2 ? String(c[2]) : "" }
}
