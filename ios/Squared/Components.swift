import SwiftUI

struct CardBox<Content: View>: View {
    @ViewBuilder var content: () -> Content
    var body: some View {
        VStack(alignment: .leading, spacing: 12) { content() }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(16)
            .background(Theme.surface)
            .clipShape(RoundedRectangle(cornerRadius: Theme.radius))
            .overlay(RoundedRectangle(cornerRadius: Theme.radius).stroke(Theme.border, lineWidth: 1))
    }
}

struct Avatar: View {
    let name: String
    var size: CGFloat = 32
    var body: some View {
        Text(initials(name))
            .font(.system(size: size * 0.4, weight: .semibold))
            .foregroundStyle(Theme.muted)
            .frame(width: size, height: size)
            .background(Theme.surface2)
            .clipShape(Circle())
            .overlay(Circle().stroke(Theme.border, lineWidth: 1))
    }
}

enum PillTone { case neutral, pos, neg }

struct Pill: View {
    let text: String
    var tone: PillTone = .neutral
    var body: some View {
        let (fg, bg): (Color, Color) = {
            switch tone {
            case .neutral: return (Theme.muted, Theme.surface2)
            case .pos: return (Theme.positive, Theme.positiveBg)
            case .neg: return (Theme.negative, Theme.negativeBg)
            }
        }()
        Text(text)
            .font(.system(size: 13, weight: .semibold))
            .foregroundStyle(fg)
            .padding(.horizontal, 10).padding(.vertical, 4)
            .background(bg)
            .clipShape(Capsule())
    }
}

struct FilledButton: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 15, weight: .semibold))
            .foregroundStyle(Theme.paper)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(Theme.ink.opacity(configuration.isPressed ? 0.85 : 1))
            .clipShape(RoundedRectangle(cornerRadius: 10))
    }
}

struct OutlineButton: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 15, weight: .medium))
            .foregroundStyle(Theme.ink)
            .padding(.horizontal, 14).padding(.vertical, 9)
            .background(configuration.isPressed ? Theme.surface2 : Theme.surface)
            .overlay(RoundedRectangle(cornerRadius: 10).stroke(Theme.border, lineWidth: 1))
            .clipShape(RoundedRectangle(cornerRadius: 10))
    }
}

struct SectionTitle: View {
    let text: String
    var body: some View {
        Text(text).font(.system(size: 22, weight: .bold)).foregroundStyle(Theme.ink)
    }
}

extension View {
    func screenBackground() -> some View {
        self.background(Theme.paper.ignoresSafeArea())
    }
}

struct LabeledInput: View {
    let label: String
    @Binding var text: String
    var placeholder: String = ""
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(label).font(.system(size: 13, weight: .semibold)).foregroundStyle(Theme.muted)
            TextField(placeholder, text: $text)
                .autocorrectionDisabled()
                .padding(.horizontal, 12).padding(.vertical, 11)
                .background(Theme.surface)
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(Theme.border, lineWidth: 1))
                .clipShape(RoundedRectangle(cornerRadius: 8))
        }
    }
}

struct SheetScaffold<Content: View>: View {
    let title: String
    @ViewBuilder var content: () -> Content
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) { content() }
                .padding(20)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .top)
                .background(Theme.paper.ignoresSafeArea())
                .navigationTitle(title)
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button { dismiss() } label: { Image(systemName: "xmark") }
                    }
                }
        }
        .presentationDetents([.medium])
    }
}
