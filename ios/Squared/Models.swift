import Foundation

struct User: Codable, Identifiable { let id: Int; let email: String; let name: String }

struct Group: Codable, Identifiable, Hashable {
    let id: Int
    let name: String
    let currency: String
    let role: String?
}

struct Member: Codable, Identifiable {
    let userId: Int
    let name: String
    let email: String
    let role: String
    var id: Int { userId }
}

struct ShareOut: Codable { let userId: Int; let amount: Int }

struct LineItem: Codable, Identifiable {
    let id: Int
    let name: String
    let price: Int
    let quantity: Int
    let shares: [String: Int]
}

struct Bill: Codable, Identifiable {
    let id: Int
    let title: String
    let payerId: Int
    let subtotal: Int
    let tax: Int
    let tip: Int
    let total: Int
    let currency: String
    let version: Int
    let lineItems: [LineItem]
    let shares: [ShareOut]
}

struct Transfer: Codable, Identifiable {
    let debtor: Int
    let creditor: Int
    let amount: Int
    var id: String { "\(debtor)-\(creditor)-\(amount)" }
}

struct Balances: Codable {
    let balances: [String: Int]
    let transfers: [Transfer]
    let baseline: Int
    let simplified: Int
    let reductionPct: Double
}

struct Payment: Codable, Identifiable {
    let id: Int
    let fromUser: Int
    let toUser: Int
    let amount: Int
    let method: String?
    let status: String
}

struct ReminderPayload: Codable {
    let owedCents: Int?
    let week: String?
}

struct AppNotification: Codable, Identifiable {
    let id: Int
    let type: String
    let payload: ReminderPayload?
    let read: Bool
}

struct ParsedItem: Codable { let name: String; let price: Int }

struct ParsedReceipt: Codable {
    let items: [ParsedItem]
    let subtotal: Int?
    let tax: Int?
    let tip: Int?
    let total: Int?
    let reconciled: Bool
    let issues: [String]
}

struct OcrJob: Codable, Identifiable {
    let id: Int
    let billId: Int
    let status: String
    let confidence: Int?
    let error: String?
    let parsed: ParsedReceipt?
}
