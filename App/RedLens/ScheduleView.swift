//
//  ScheduleView.swift
//  RedLens
//
//  Created by 贾真 on 2026/1/14.
//

import SwiftUI

struct ScheduleView: View {
    @ObservedObject var store: MatchStore
    @AppStorage("showScores") private var showScores = true
    // 注意：这里需要传入 navManager 才能跳转
    // 简单起见，这里先不传，或者你需要从 HomeView 传过来。
    // 为了让代码能跑，这里暂时只做展示，或者你可以把 NavigationManager 变成单例。
    
    var body: some View {
        List {
            ForEach(store.matches) { match in
                HStack {
                    Text(match.date)
                    Text(match.opponent)
                    Spacer()
                    if match.isFinished && showScores {
                        Text(match.score)
                    } else {
                        Text(match.time)
                    }
                }
            }
        }
    }
}
