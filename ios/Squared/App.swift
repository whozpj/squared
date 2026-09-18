import SwiftUI

@main
struct SquaredApp: App {
    @StateObject private var app = AppState()
    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(app)
                .tint(Theme.ink)
                .task { await app.bootstrap() }
        }
    }
}

struct RootView: View {
    @EnvironmentObject var app: AppState
    var body: some View {
        SwiftUI.Group {
            if app.booting {
                ProgressView().screenBackground().frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if app.user != nil {
                GroupsView()
            } else {
                LoginView()
            }
        }
    }
}
