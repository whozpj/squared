import SwiftUI

struct NotificationsView: View {
    @EnvironmentObject var app: AppState
    @Environment(\.dismiss) var dismiss
    @State private var items: [AppNotification] = []
    @State private var loaded = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    if loaded && items.isEmpty {
                        Text("You're all caught up.")
                            .font(.system(size: 14)).foregroundStyle(Theme.muted)
                            .frame(maxWidth: .infinity).padding(.top, 40)
                    }
                    ForEach(items) { n in
                        Button { mark(n) } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 3) {
                                    Text("Payment reminder").font(.system(size: 15, weight: .semibold)).foregroundStyle(Theme.ink)
                                    Text("You owe \(money(n.payload?.owedCents ?? 0)) this week")
                                        .font(.system(size: 13)).foregroundStyle(Theme.muted).monospacedDigit()
                                }
                                Spacer()
                                if !n.read { Circle().fill(Theme.negative).frame(width: 8, height: 8) }
                            }
                            .padding(.vertical, 14)
                            .opacity(n.read ? 0.55 : 1)
                        }.buttonStyle(.plain)
                        Divider().background(Theme.border)
                    }
                }
                .padding(.horizontal, 16)
            }
            .background(Theme.paper.ignoresSafeArea())
            .navigationTitle("Notifications")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Sign out", role: .destructive) { app.logout(); dismiss() }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button { dismiss() } label: { Image(systemName: "xmark") }
                }
            }
            .task { await load() }
        }
    }

    private func mark(_ n: AppNotification) {
        guard !n.read else { return }
        Task { _ = try? await API.shared.markRead(n.id); await load() }
    }
    private func load() async {
        items = (try? await API.shared.notifications()) ?? []
        loaded = true
    }
}
