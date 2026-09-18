import SwiftUI

@MainActor
final class AppState: ObservableObject {
    @Published var user: User?
    @Published var booting = true

    private let tokenKey = "squared_token"

    func bootstrap() async {
        if let t = UserDefaults.standard.string(forKey: tokenKey) {
            API.shared.token = t
            do { user = try await API.shared.me() } catch { logout() }
        }
        booting = false
    }

    func login(email: String, name: String) async throws {
        let r = try await API.shared.devLogin(email: email, name: name.isEmpty ? email : name)
        API.shared.token = r.accessToken
        UserDefaults.standard.set(r.accessToken, forKey: tokenKey)
        user = try await API.shared.me()
    }

    func logout() {
        API.shared.token = nil
        UserDefaults.standard.removeObject(forKey: tokenKey)
        user = nil
    }
}

struct BillRoute: Hashable { let gid: Int; let billId: Int; let title: String }
