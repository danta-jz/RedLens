import SwiftUI

@main
struct RedLensApp: App {
    @StateObject private var store = MatchStore()
    
    var body: some Scene {
        WindowGroup {
            // 使用 NavigationView 包裹首页，启用导航功能
            NavigationView {
                HomeView(store: store)
            }
            .accentColor(.arsenalRed)
            .preferredColorScheme(.light)
        }
    }
}
