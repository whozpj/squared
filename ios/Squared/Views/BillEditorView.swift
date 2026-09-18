import PhotosUI
import SwiftUI

private struct EditRow: Identifiable {
    let id = UUID()
    var name: String
    var priceText: String
    var members: Set<Int>
}

struct BillEditorView: View {
    let route: BillRoute
    @Environment(\.dismiss) var dismiss

    @State private var members: [Member] = []
    @State private var rows: [EditRow] = []
    @State private var taxText = ""
    @State private var tipText = ""
    @State private var version: Int?
    @State private var loaded = false
    @State private var saving = false

    @State private var pickerItem: PhotosPickerItem?
    @State private var ocrBusy = false
    @State private var ocrNote: (ok: Bool, issues: [String])?

    private func dollars(_ s: String) -> Int { Int(round((Double(s) ?? 0) * 100)) }
    private var subtotal: Int { rows.reduce(0) { $0 + dollars($1.priceText) } }
    private var total: Int { subtotal + dollars(taxText) + dollars(tipText) }
    private var unassigned: Bool { rows.contains { $0.members.isEmpty } }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                receiptCard
                itemsCard
                totalsCard
                HStack {
                    Spacer()
                    Button("Save bill") { save() }
                        .buttonStyle(FilledButton())
                        .frame(width: 160)
                        .disabled(saving || rows.isEmpty || unassigned)
                }
                if unassigned {
                    Text("Assign every item to someone first.")
                        .font(.system(size: 13)).foregroundStyle(Theme.negative)
                        .frame(maxWidth: .infinity, alignment: .trailing)
                }
            }
            .padding(16)
        }
        .background(Theme.paper.ignoresSafeArea())
        .navigationTitle(route.title)
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
        .onChange(of: pickerItem) { _, item in if let item { handlePick(item) } }
    }

    private var receiptCard: some View {
        CardBox {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Scan a receipt").font(.system(size: 16, weight: .semibold))
                    Text("We'll read the line items — you review before splitting.")
                        .font(.system(size: 13)).foregroundStyle(Theme.muted)
                }
                Spacer()
                PhotosPicker(selection: $pickerItem, matching: .images) {
                    if ocrBusy { ProgressView() } else { Label("Upload", systemImage: "camera") }
                }.buttonStyle(OutlineButton())
            }
            if let n = ocrNote {
                if n.ok {
                    Pill(text: "Reads add up", tone: .pos)
                } else {
                    Pill(text: "Needs review", tone: .neg)
                    ForEach(n.issues, id: \.self) { Text($0).font(.system(size: 12)).foregroundStyle(Theme.muted) }
                }
            }
        }
    }

    private var itemsCard: some View {
        CardBox {
            HStack {
                Text("Items").font(.system(size: 16, weight: .semibold))
                Spacer()
                Button("+ Add item") { rows.append(EditRow(name: "", priceText: "", members: Set(members.map(\.userId)))) }
                    .font(.system(size: 14)).foregroundStyle(Theme.muted)
            }
            if rows.isEmpty {
                Text("Add items manually, or upload a receipt above.")
                    .font(.system(size: 14)).foregroundStyle(Theme.muted).padding(.vertical, 8)
            }
            ForEach($rows) { $row in
                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 8) {
                        TextField("Item", text: $row.name)
                            .padding(.horizontal, 10).padding(.vertical, 9)
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.border, lineWidth: 1))
                        TextField("0.00", text: $row.priceText)
                            .keyboardType(.decimalPad).multilineTextAlignment(.trailing).monospacedDigit()
                            .frame(width: 90)
                            .padding(.horizontal, 10).padding(.vertical, 9)
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.border, lineWidth: 1))
                        Button { rows.removeAll { $0.id == row.id } } label: { Image(systemName: "xmark").foregroundStyle(Theme.muted) }
                    }
                    chips(for: $row)
                }
                .padding(.vertical, 6)
                if row.id != rows.last?.id { Divider().background(Theme.border) }
            }
        }
    }

    private func chips(for row: Binding<EditRow>) -> some View {
        let count = row.wrappedValue.members.count
        return HStack(spacing: 6) {
            ForEach(members) { m in
                let on = row.wrappedValue.members.contains(m.userId)
                Button {
                    if on { row.wrappedValue.members.remove(m.userId) } else { row.wrappedValue.members.insert(m.userId) }
                } label: {
                    Text(m.name.split(separator: " ").first.map(String.init) ?? m.name)
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(on ? Theme.paper : Theme.muted)
                        .padding(.horizontal, 10).padding(.vertical, 4)
                        .background(on ? Theme.ink : Theme.surface2)
                        .clipShape(Capsule())
                }.buttonStyle(.plain)
            }
            if count > 0 {
                Text("\(money(dollars(row.wrappedValue.priceText) / max(count, 1))) each")
                    .font(.system(size: 12)).foregroundStyle(Theme.faint).monospacedDigit()
            }
            Spacer()
        }
    }

    private var totalsCard: some View {
        CardBox {
            totalsRow("Subtotal", value: money(subtotal))
            HStack { Text("Tax").foregroundStyle(Theme.muted); Spacer(); miniField($taxText) }
            HStack { Text("Tip").foregroundStyle(Theme.muted); Spacer(); miniField($tipText) }
            Divider().background(Theme.border)
            HStack {
                Text("Total").font(.system(size: 16, weight: .bold))
                Spacer()
                Text(money(total)).font(.system(size: 18, weight: .bold)).monospacedDigit()
            }
            Text("Tax & tip are split in proportion to what each person ordered.")
                .font(.system(size: 12)).foregroundStyle(Theme.faint)
        }
    }

    private func totalsRow(_ label: String, value: String) -> some View {
        HStack { Text(label).foregroundStyle(Theme.muted); Spacer(); Text(value).monospacedDigit() }
    }
    private func miniField(_ text: Binding<String>) -> some View {
        TextField("0.00", text: text)
            .keyboardType(.decimalPad).multilineTextAlignment(.trailing).monospacedDigit()
            .frame(width: 90).padding(.horizontal, 10).padding(.vertical, 8)
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.border, lineWidth: 1))
    }

    private func handlePick(_ item: PhotosPickerItem) {
        ocrBusy = true; ocrNote = nil
        Task {
            defer { ocrBusy = false; pickerItem = nil }
            guard let data = try? await item.loadTransferable(type: Data.self) else { return }
            do {
                let started = try await API.shared.uploadReceipt(route.billId, image: data)
                var job = started
                for _ in 0..<20 {
                    if job.status == "done" || job.status == "failed" { break }
                    try? await Task.sleep(nanoseconds: 700_000_000)
                    job = try await API.shared.job(started.id)
                }
                if let p = job.parsed {
                    rows = p.items.map { EditRow(name: $0.name, priceText: String(format: "%.2f", Double($0.price) / 100), members: Set(members.map(\.userId))) }
                    if let t = p.tax { taxText = String(format: "%.2f", Double(t) / 100) }
                    if let t = p.tip { tipText = String(format: "%.2f", Double(t) / 100) }
                    ocrNote = (p.reconciled, p.issues)
                } else {
                    ocrNote = (false, [job.error ?? "Couldn't read the receipt"])
                }
            } catch {
                ocrNote = (false, ["Upload failed"])
            }
        }
    }

    private func save() {
        saving = true
        Task {
            let items = rows.map { r in
                ItemInput(name: r.name.isEmpty ? "Item" : r.name,
                          price: dollars(r.priceText),
                          shares: Dictionary(uniqueKeysWithValues: r.members.map { (String($0), 1) }))
            }
            _ = try? await API.shared.replaceItems(route.billId, ItemsReplace(
                tax: dollars(taxText), tip: dollars(tipText), items: items, version: version))
            saving = false
            dismiss()
        }
    }

    private func load() async {
        async let m = API.shared.members(route.gid)
        async let b = API.shared.getBill(route.billId)
        members = (try? await m) ?? []
        if let bill = try? await b {
            version = bill.version
            taxText = bill.tax > 0 ? String(format: "%.2f", Double(bill.tax) / 100) : ""
            tipText = bill.tip > 0 ? String(format: "%.2f", Double(bill.tip) / 100) : ""
            rows = bill.lineItems.map { li in
                EditRow(name: li.name,
                        priceText: String(format: "%.2f", Double(li.price) / 100),
                        members: Set(li.shares.keys.compactMap { Int($0) }))
            }
        }
        loaded = true
    }
}
