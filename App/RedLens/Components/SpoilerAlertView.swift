//
//  SpoilerAlertView.swift
//  RedLens
//
//  Created by 贾真 on 2026/1/15.
//

import SwiftUI

struct SpoilerAlertView: View {
    // 闭包：用来告诉父页面，用户点了“确认”还是“取消”
    var onConfirm: () -> Void
    var onCancel: () -> Void
    
    var body: some View {
        ZStack {
            // 半透明黑色遮罩
            Color.black.opacity(0.8).edgesIgnoringSafeArea(.all)
            
            VStack(spacing: 24) {
                // 图标
                Image(systemName: "eye.slash.fill")
                    .font(.system(size: 60))
                    .foregroundColor(.white)
                
                // 标题
                Text("防剧透预警")
                    .font(.title2).bold()
                    .foregroundColor(.white)
                
                // 说明文案
                Text("咪咕视频录像页顶部会直接显示比分。\n\n请在跳转前，准备好\n🖐️ 用手遮挡屏幕顶部 🖐️")
                    .multilineTextAlignment(.center) // 文字居中
                    .foregroundColor(.white.opacity(0.8))
                    .padding(.horizontal)
                
                // 按钮组
                VStack(spacing: 12) {
                    // 确认按钮
                    Button(action: onConfirm) {
                        Text("我已准备好，跳转观看")
                            .font(.headline)
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .padding()
                            .background(Color.arsenalRed) // 这里自动用到了你刚才创建的颜色
                            .cornerRadius(12)
                    }
                    
                    // 取消按钮
                    Button(action: onCancel) {
                        Text("取消")
                            .font(.subheadline)
                            .foregroundColor(.white.opacity(0.6))
                    }
                }
                .padding(.top, 10)
            }
            .padding(30)
            .background(Color.darkCardBg) // 这里也用到了自定义颜色
            .cornerRadius(20)
            .padding(40) // 外边距，防止贴边
        }
    }
}

#Preview {
    SpoilerAlertView(onConfirm: {}, onCancel: {})
}
