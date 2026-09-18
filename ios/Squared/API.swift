import Foundation

struct APIError: Error, LocalizedError {
    let status: Int
    let detail: String
    var errorDescription: String? { detail }
}

/// Talks to the FastAPI backend. The simulator reaches the Mac host via localhost.
final class API {
    static let shared = API()
    var baseURL = URL(string: "http://localhost:8001")!
    var token: String?

    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()
    private let encoder: JSONEncoder = {
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        return e
    }()

    private func send<T: Decodable>(_ method: String, _ path: String, body: Data? = nil) async throws -> T {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = method
        if let body { req.httpBody = body; req.setValue("application/json", forHTTPHeaderField: "Content-Type") }
        if let token { req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        let (data, resp) = try await URLSession.shared.data(for: req)
        let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
        guard (200..<300).contains(code) else {
            let detail = (try? JSONDecoder().decode([String: String].self, from: data))?["detail"] ?? "Error \(code)"
            throw APIError(status: code, detail: detail)
        }
        if T.self == Empty.self { return Empty() as! T }
        return try decoder.decode(T.self, from: data)
    }

    private func enc(_ v: Encodable) throws -> Data { try encoder.encode(AnyEncodable(v)) }

    // Auth
    func devLogin(email: String, name: String) async throws -> TokenResponse {
        try await send("POST", "/auth/dev-login", body: try enc(["email": email, "name": name]))
    }
    func me() async throws -> User { try await send("GET", "/auth/me") }

    // Groups
    func groups() async throws -> [Group] { try await send("GET", "/groups") }
    func createGroup(name: String) async throws -> Group {
        try await send("POST", "/groups", body: try enc(["name": name, "currency": "USD"]))
    }
    func members(_ gid: Int) async throws -> [Member] { try await send("GET", "/groups/\(gid)/members") }
    func createInvite(_ gid: Int) async throws -> Invite {
        try await send("POST", "/groups/\(gid)/invites", body: try enc([String: String]()))
    }
    func acceptInvite(_ token: String) async throws -> Group {
        try await send("POST", "/invites/\(token)/accept")
    }

    // Bills & balances
    func balances(_ gid: Int) async throws -> Balances { try await send("GET", "/groups/\(gid)/balances") }
    func bills(_ gid: Int) async throws -> [Bill] { try await send("GET", "/groups/\(gid)/bills") }
    func getBill(_ id: Int) async throws -> Bill { try await send("GET", "/bills/\(id)") }
    func createBill(_ gid: Int, _ body: BillCreate) async throws -> Bill {
        try await send("POST", "/groups/\(gid)/bills", body: try encoder.encode(body))
    }
    func replaceItems(_ id: Int, _ body: ItemsReplace) async throws -> Bill {
        try await send("PUT", "/bills/\(id)/items", body: try encoder.encode(body))
    }

    // Payments
    func payments(_ gid: Int) async throws -> [Payment] { try await send("GET", "/groups/\(gid)/payments") }
    func claimPayment(_ gid: Int, to: Int, amount: Int) async throws -> Payment {
        try await send("POST", "/groups/\(gid)/payments", body: try enc(["to_user": to, "amount": amount] as [String: Int]))
    }
    func confirmPayment(_ id: Int) async throws -> Payment { try await send("POST", "/payments/\(id)/confirm") }

    // Notifications
    func notifications() async throws -> [AppNotification] { try await send("GET", "/notifications") }
    func markRead(_ id: Int) async throws -> AppNotification { try await send("POST", "/notifications/\(id)/read") }

    // OCR
    func job(_ id: Int) async throws -> OcrJob { try await send("GET", "/ocr/\(id)") }
    func uploadReceipt(_ billId: Int, image: Data, filename: String = "receipt.jpg") async throws -> OcrJob {
        let boundary = "Boundary-\(UUID().uuidString)"
        var req = URLRequest(url: baseURL.appendingPathComponent("/bills/\(billId)/ocr"))
        req.httpMethod = "POST"
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        if let token { req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(image)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
        let (data, resp) = try await URLSession.shared.upload(for: req, from: body)
        let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
        guard (200..<300).contains(code) else { throw APIError(status: code, detail: "Upload failed (\(code))") }
        return try decoder.decode(OcrJob.self, from: data)
    }
}

struct Empty: Decodable {}
struct TokenResponse: Decodable { let accessToken: String; let userId: Int }
struct Invite: Decodable { let id: Int; let token: String; let status: String }

struct ItemInput: Encodable {
    let name: String
    let price: Int
    var quantity: Int = 1
    let shares: [String: Int]
}
struct BillCreate: Encodable {
    let title: String
    let payerId: Int
    let tax: Int
    let tip: Int
    let items: [ItemInput]
}
struct ItemsReplace: Encodable {
    let tax: Int
    let tip: Int
    let items: [ItemInput]
    let version: Int?
}

/// Type-erased Encodable so simple dictionaries can be encoded through the shared encoder.
struct AnyEncodable: Encodable {
    private let encodeFunc: (Encoder) throws -> Void
    init(_ wrapped: Encodable) { encodeFunc = wrapped.encode }
    func encode(to encoder: Encoder) throws { try encodeFunc(encoder) }
}
