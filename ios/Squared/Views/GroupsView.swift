import SwiftUI

struct GroupsView: View {
    @EnvironmentObject var app: AppState
    @State private var groups: [Group] = []
    @State private var loaded = false
    @State private var showNew = false
    @State private var showJoin = false
    @State private var showNotifs = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if !loaded {
                        ProgressView().frame(maxWidth: .infinity).padding(.top, 40)
                    } else if groups.isEmpty {
                        CardBox {
                            VStack(spacing: 6) {
                                Text("No groups yet").font(.system(size: 16, weight: .semibold))
                                Text("Create a group for your roommates or trip, then add a bill.")
                                    .font(.system(size: 14)).foregroundStyle(Theme.muted)
                                    .multilineTextAlignment(.center)
                            }.frame(maxWidth: .infinity).padding(.vertical, 24)
                        }
                    } else {
                        CardBox {
                            ForEach(Array(groups.enumerated()), id: \.element.id) { idx, g in
                                NavigationLink(value: g) {
                                    HStack(spacing: 12) {
                                        Image(systemName: "person.2.fill").foregroundStyle(Theme.muted)
                                            .frame(width: 32, height: 32).background(Theme.surface2).clipShape(Circle())
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text(g.name).font(.system(size: 16, weight: .semibold)).foregroundStyle(Theme.ink)
                                            Text(g.currency).font(.system(size: 13)).foregroundStyle(Theme.muted)
                                        }
                                        Spacer()
                                        Image(systemName: "chevron.right").foregroundStyle(Theme.faint).font(.system(size: 14, weight: .semibold))
                                    }.padding(.vertical, 10)
                                }
                                if idx < groups.count - 1 { Divider().background(Theme.border) }
                            }
                        }
                    }
                }
                .padding(16)
            }
            .background(Theme.paper.ignoresSafeArea())
            .navigationTitle("Groups")
            .navigationDestination(for: Group.self) { GroupDetailView(group: $0) }
            .navigationDestination(for: BillRoute.self) { BillEditorView(route: $0) }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button { showNotifs = true } label: { Image(systemName: "bell") }
                }
                ToolbarItemGroup(placement: .topBarTrailing) {
                    Button("Join") { showJoin = true }
                    Button { showNew = true } label: { Image(systemName: "plus") }
                }
            }
            .sheet(isPresented: $showNew) { NewGroupSheet(onDone: reload) }
            .sheet(isPresented: $showJoin) { JoinSheet(onDone: reload) }
            .sheet(isPresented: $showNotifs) { NotificationsView() }
            .task { await load() }
            .refreshable { await load() }
        }
    }

    private func load() async {
        do { groups = try await API.shared.groups() } catch {}
        loaded = true
    }
    private func reload() { Task { await load() } }
}

private struct NewGroupSheet: View {
    @Environment(\.dismiss) var dismiss
    let onDone: () -> Void
    @State private var name = ""
    @State private var busy = false
    var body: some View {
        SheetScaffold(title: "New group") {
            LabeledInput(label: "Group name", text: $name, placeholder: "Roommates, Tahoe trip…")
            Button { create() } label: { busy ? AnyView(ProgressView().tint(Theme.paper)) : AnyView(Text("Create group")) }
                .buttonStyle(FilledButton()).disabled(busy || name.isEmpty)
        }
    }
    private func create() {
        busy = true
        Task { _ = try? await API.shared.createGroup(name: name); onDone(); dismiss() }
    }
}

private struct JoinSheet: View {
    @Environment(\.dismiss) var dismiss
    let onDone: () -> Void
    @State private var code = ""
    @State private var busy = false
    var body: some View {
        SheetScaffold(title: "Join a group") {
            LabeledInput(label: "Invite code", text: $code, placeholder: "paste code")
            Button { join() } label: { busy ? AnyView(ProgressView().tint(Theme.paper)) : AnyView(Text("Join group")) }
                .buttonStyle(FilledButton()).disabled(busy || code.isEmpty)
        }
    }
    private func join() {
        busy = true
        Task { _ = try? await API.shared.acceptInvite(code.trimmingCharacters(in: .whitespaces)); onDone(); dismiss() }
    }
}
