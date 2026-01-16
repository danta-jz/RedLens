//
//  Color+Extension.swift
//  RedLens
//
//  Created by 贾真 on 2026/1/15.
//

import SwiftUI

// 扩展系统自带的 Color 功能，加入自定义颜色
extension Color {
    // 阿森纳主色红 (参考截图取色)
    static let arsenalRed = Color(red: 228/255, green: 3/255, blue: 45/255)
    
    // 深色卡片背景 (接近黑色，带一点蓝调)
    static let darkCardBg = Color(red: 16/255, green: 20/255, blue: 28/255)
    
    // 辅助灰 (用于不太重要的文字)
    static let textGray = Color(red: 142/255, green: 142/255, blue: 147/255)
    
    // 全局背景灰 (整个APP的底色)
    static let backgroundGray = Color(red: 242/255, green: 242/255, blue: 247/255)
}
