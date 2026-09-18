import SwiftUI

struct LoginView: View {
    @EnvironmentObject var app: AppState
    @State private var email = ""
    @State private var name = ""
    @State private var busy = false
    @State private var error: String?

    var body: some View {
        ZStack {
            Theme.paper.ignoresSafeArea()
            VStack(spacing: 0) {
                HStack(spacing: 8) {
                    RoundedRectangle(cornerRadius: 6).stroke(Theme.ink, lineWidth: 2.5).frame(width: 26, height: 26)
                    Text("Squared").font(.system(size: 26, weight: .bold))
                }
                Text("Split bills fairly. Settle up in the fewest payments.")
                    .font(.system(size: 15)).foregroundStyle(Theme.muted)
                    .multilineTextAlignment(.center).padding(.top, 8).padding(.bottom, 28)

                CardBox {
                    field("Email", text: $email, keyboard: .emailAddress)
                    field("Name", text: $name)
                    if let error {
                        Text(error).font(.system(size: 13)).foregroundStyle(Theme.negative)
                    }
                    Button(action: submit) {
                        if busy { ProgressView().tint(Theme.paper) } else { Text("Continue") }
                    }
                    .buttonStyle(FilledButton()).disabled(busy)
                }
                Text("Sign in with Google coming soon.")
                    .font(.system(size: 13)).foregroundStyle(Theme.faint).padding(.top, 16)
            }
            .padding(24)
            .frame(maxWidth: 420)
        }
    }

    @ViewBuilder
    private func field(_ label: String, text: Binding<String>, keyboard: UIKeyboardType = .default) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(label).font(.system(size: 13, weight: .semibold)).foregroundStyle(Theme.muted)
            TextField("", text: text)
                .textInputAutocapitalization(keyboard == .emailAddress ? .never : .words)
                .autocorrectionDisabled()
                .keyboardType(keyboard)
                .padding(.horizontal, 12).padding(.vertical, 11)
                .background(Theme.surface)
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.border, lineWidth: 1))
                .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }

    private func submit() {
        busy = true; error = nil
        Task {
            do { try await app.login(email: email.trimmingCharacters(in: .whitespaces), name: name) }
            catch { self.error = "Couldn't sign in. Is the backend running?" }
            busy = false
        }
    }
}
