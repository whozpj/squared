import SwiftUI

extension Color {
    init(hex: UInt) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xff) / 255,
            green: Double((hex >> 8) & 0xff) / 255,
            blue: Double(hex & 0xff) / 255,
            opacity: 1
        )
    }
}

/// Warm off-white palette — mirrors the web app. No gradients; money is the only color.
enum Theme {
    static let paper = Color(hex: 0xFAF8F4)
    static let surface = Color.white
    static let surface2 = Color(hex: 0xF4F1EA)
    static let ink = Color(hex: 0x1C1B18)
    static let muted = Color(hex: 0x77726A)
    static let faint = Color(hex: 0xA8A29A)
    static let border = Color(hex: 0xE7E3DA)
    static let positive = Color(hex: 0x2E7D57)
    static let positiveBg = Color(hex: 0xE8F1EC)
    static let negative = Color(hex: 0xC1492E)
    static let negativeBg = Color(hex: 0xF6E9E5)
    static let radius: CGFloat = 14
}

func money(_ cents: Int) -> String {
    let v = String(format: "%.2f", Double(abs(cents)) / 100)
    return "\(cents < 0 ? "-" : "")$\(v)"
}

func initials(_ name: String) -> String {
    let parts = name.split(separator: " ")
    return parts.prefix(2).compactMap { $0.first }.map(String.init).joined().uppercased()
}
