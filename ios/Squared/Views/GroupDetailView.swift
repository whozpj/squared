import SwiftUI

struct GroupDetailView: View {
    let group: Group
    @EnvironmentObject var app: AppState

    @State private var members: [Member] = []
    @State private var balances: Balances?
    @State private var bills: [Bill] = []
    @State private var payments: [Payment] = []
    @State private var showAddBill = false
    @State private var showInvite = false

    private func name(_ id: Int) -> String { members.first { $0.userId == id }?.name ?? "User \(id)" }
    private var myBalance: Int { balances?.balances[String(app.user?.id ?? -1)] ?? 0 }
    private var pendingForMe: [Payment] {
        payments.filter { $0.toUser == app.user?.id && $0.status == "claimed" }
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                membersRow
                balanceCard
                settleCard
                SectionTitle(text: "Bills").padding(.top, 8)
                billsCard
            }
            .padding(16)
        }
        .background(Theme.paper.ignoresSafeArea())
        .navigationTitle(group.name)
        .navigationBarTitleDisplayMode(.large)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { showAddBill = true } label: { Label("Add bill", systemImage: "plus") }
            }
        }
        .sheet(isPresented: $showAddBill) {
            AddBillSheet(group: group, members: members, defaultPayer: app.user?.id ?? 0) { Task { await load() } }
        }
        .sheet(isPresented: $showInvite) { InviteSheet(gid: group.id) }
        .task { await load() }
        .refreshable { await load() }
    }

    private var membersRow: some View {
        HStack(spacing: 6) {
            ForEach(members) { m in Avatar(name: m.name) }
            Button { showInvite = true } label: {
                Image(systemName: "plus").foregroundStyle(Theme.muted)
                    .frame(width: 32, height: 32).overlay(Circle().stroke(Theme.border, lineWidth: 1))
            }
            Spacer()
        }
    }

    private var balanceCard: some View {
        CardBox {
            Text("Your balance").font(.system(size: 13)).foregroundStyle(Theme.muted)
            HStack(alignment: .firstTextBaseline) {
                Text(money(myBalance))
                    .font(.system(size: 30, weight: .bold))
                    .monospacedDigit()
                    .foregroundStyle(myBalance > 0 ? Theme.positive : myBalance < 0 ? Theme.negative : Theme.ink)
                Spacer()
                Text(myBalance > 0 ? "you're owed" : myBalance < 0 ? "you owe" : "settled up")
                    .font(.system(size: 13)).foregroundStyle(Theme.muted)
            }
        }
    }

    @ViewBuilder private var settleCard: some View {
        CardBox {
            HStack {
                SectionTitle(text: "Settle up")
                Spacer()
                if let b = balances, b.baseline > 0 {
                    Pill(text: "\(b.baseline) → \(b.simplified) payments", tone: b.reductionPct > 0 ? .pos : .neutral)
                }
            }
            if let b = balances, b.transfers.isEmpty {
                Text("Everyone's settled up.").font(.system(size: 14)).foregroundStyle(Theme.muted).padding(.vertical, 8)
            } else if let b = balances {
                ForEach(b.transfers) { t in transferRow(t) }
            }
            if !pendingForMe.isEmpty {
                Divider().background(Theme.border)
                Text("Confirm payments sent to you").font(.system(size: 13)).foregroundStyle(Theme.muted)
                ForEach(pendingForMe) { p in
                    HStack {
                        Text("\(name(p.fromUser)) paid you \(money(p.amount))").font(.system(size: 14))
                        Spacer()
                        Button("Confirm") { Task { _ = try? await API.shared.confirmPayment(p.id); await load() } }
                            .buttonStyle(OutlineButton())
                    }
                }
            }
        }
    }

    @ViewBuilder private func transferRow(_ t: Transfer) -> some View {
        let mine = t.debtor == app.user?.id
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Avatar(name: name(t.debtor), size: 28)
                Image(systemName: "arrow.right").font(.system(size: 12)).foregroundStyle(Theme.muted)
                Avatar(name: name(t.creditor), size: 28)
                Text("\(mine ? "You" : name(t.debtor)) → \(name(t.creditor))")
                    .font(.system(size: 13)).foregroundStyle(Theme.muted).lineLimit(1)
                Spacer()
                Text(money(t.amount)).font(.system(size: 15, weight: .semibold)).monospacedDigit()
            }
            if mine {
                HStack {
                    Spacer()
                    if let url = venmoURL(amount: t.amount) {
                        Link("Venmo", destination: url).buttonStyle(OutlineButton())
                    }
                    Button("I paid") {
                        Task { _ = try? await API.shared.claimPayment(group.id, to: t.creditor, amount: t.amount); await load() }
                    }.buttonStyle(OutlineButton())
                }
            }
        }
        .padding(.vertical, 6)
    }

    @ViewBuilder private var billsCard: some View {
        if bills.isEmpty {
            CardBox {
                Text("No bills yet — add one or snap a receipt.")
                    .font(.system(size: 14)).foregroundStyle(Theme.muted)
                    .frame(maxWidth: .infinity).padding(.vertical, 16)
            }
        } else {
            CardBox {
                ForEach(Array(bills.enumerated()), id: \.element.id) { idx, b in
                    NavigationLink(value: BillRoute(gid: group.id, billId: b.id, title: b.title)) {
                        HStack(spacing: 12) {
                            Image(systemName: "doc.text").foregroundStyle(Theme.muted)
                                .frame(width: 32, height: 32).background(Theme.surface2).clipShape(Circle())
                            VStack(alignment: .leading, spacing: 2) {
                                Text(b.title.isEmpty ? "Untitled bill" : b.title)
                                    .font(.system(size: 16, weight: .semibold)).foregroundStyle(Theme.ink)
                                Text("\(name(b.payerId)) paid").font(.system(size: 13)).foregroundStyle(Theme.muted)
                            }
                            Spacer()
                            Text(money(b.total)).font(.system(size: 15, weight: .semibold)).monospacedDigit().foregroundStyle(Theme.ink)
                            Image(systemName: "chevron.right").foregroundStyle(Theme.faint).font(.system(size: 13, weight: .semibold))
                        }.padding(.vertical, 10)
                    }
                    if idx < bills.count - 1 { Divider().background(Theme.border) }
                }
            }
        }
    }

    private func venmoURL(amount: Int) -> URL? {
        var c = URLComponents(string: "https://venmo.com/")
        c?.queryItems = [
            .init(name: "txn", value: "pay"),
            .init(name: "amount", value: String(format: "%.2f", Double(amount) / 100)),
            .init(name: "note", value: "\(group.name) settle up"),
        ]
        return c?.url
    }

    private func load() async {
        async let m = API.shared.members(group.id)
        async let b = API.shared.balances(group.id)
        async let bl = API.shared.bills(group.id)
        async let p = API.shared.payments(group.id)
        members = (try? await m) ?? members
        balances = (try? await b) ?? balances
        bills = (try? await bl) ?? bills
        payments = (try? await p) ?? payments
    }
}

private struct AddBillSheet: View {
    @Environment(\.dismiss) var dismiss
    let group: Group
    let members: [Member]
    let defaultPayer: Int
    let onDone: () -> Void
    @State private var title = ""
    @State private var payer: Int = 0
    @State private var busy = false

    var body: some View {
        SheetScaffold(title: "Add a bill") {
            LabeledInput(label: "What's it for?", text: $title, placeholder: "Dinner, groceries…")
            VStack(alignment: .leading, spacing: 6) {
                Text("Who paid?").font(.system(size: 13, weight: .semibold)).foregroundStyle(Theme.muted)
                Picker("Who paid?", selection: $payer) {
                    ForEach(members) { m in Text(m.name).tag(m.userId) }
                }.pickerStyle(.menu).tint(Theme.ink)
            }
            Button { create() } label: { busy ? AnyView(ProgressView().tint(Theme.paper)) : AnyView(Text("Continue")) }
                .buttonStyle(FilledButton()).disabled(busy)
        }
        .onAppear { payer = defaultPayer }
    }

    private func create() {
        busy = true
        Task {
            _ = try? await API.shared.createBill(group.id, BillCreate(
                title: title.isEmpty ? "New bill" : title, payerId: payer, tax: 0, tip: 0, items: []))
            onDone(); dismiss()
        }
    }
}

private struct InviteSheet: View {
    let gid: Int
    @State private var code: String?
    @State private var busy = false
    var body: some View {
        SheetScaffold(title: "Invite someone") {
            Text("Generate a code and share it. They tap “Join” and paste it.")
                .font(.system(size: 14)).foregroundStyle(Theme.muted)
            if let code {
                Text(code).font(.system(size: 14, design: .monospaced))
                    .padding(12).frame(maxWidth: .infinity, alignment: .leading)
                    .background(Theme.surface2).clipShape(RoundedRectangle(cornerRadius: 8))
                    .textSelection(.enabled)
            } else {
                Button { gen() } label: { busy ? AnyView(ProgressView().tint(Theme.paper)) : AnyView(Text("Generate invite code")) }
                    .buttonStyle(FilledButton()).disabled(busy)
            }
        }
    }
    private func gen() {
        busy = true
        Task { code = (try? await API.shared.createInvite(gid))?.token; busy = false }
    }
}
