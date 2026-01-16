//
//  TeamLogoView.swift
//  RedLens
//
//  Created by 贾真 on 2026/1/15.
//

import SwiftUI

struct TeamLogoView: View {
    let name: String
    let size: CGFloat
    
    var body: some View {
        // 尝试加载 Assets 中的图片
        // 逻辑：如果 Assets 里有这个名字的图，就显示图；否则显示一个圆圈和首字母（兜底）
        if UIImage(named: name) != nil {
            Image(name)
                .resizable()
                .scaledToFit()
                .frame(width: size, height: size)
        } else {
            // 兜底 UI (当找不到图片时显示)
            ZStack {
                Circle().fill(Color.white.opacity(0.9))
                // 取名字的第一个字母
                Text(String(name.prefix(1)))
                    .font(.system(size: size * 0.4, weight: .bold))
                    .foregroundColor(.black)
            }
            .frame(width: size, height: size)
        }
    }
}

// 这是预览代码，方便你在 Xcode右侧直接看效果，不会影响打包
#Preview {
    ZStack {
        Color.black
        TeamLogoView(name: "Arsenal", size: 80)
    }
}
