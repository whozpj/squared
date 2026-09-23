// Animated hero for the welcome screen: shows tangled pairwise payments
// collapsing into one simplified transfer — the product's core idea. Pure CSS
// crossfade between two states; respects prefers-reduced-motion (see index.css).

function Node({ x, y, label }: { x: number; y: number; label: string }) {
  return (
    <g>
      <circle cx={x} cy={y} r="18" fill="var(--surface-2)" stroke="var(--border)" />
      <text
        x={x}
        y={y + 4}
        textAnchor="middle"
        fontSize="13"
        fontWeight="600"
        fill="var(--muted)"
      >
        {label}
      </text>
    </g>
  );
}

export function WelcomeDemo() {
  return (
    <div className="welcome-demo" aria-hidden>
      {/* Before: three tangled payments */}
      <svg className="hero-layer hero-a" viewBox="0 0 300 150">
        <defs>
          <marker id="ah" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="var(--faint)" />
          </marker>
        </defs>
        <path d="M62 44 C 110 20, 190 20, 238 44" fill="none" stroke="var(--faint)" strokeWidth="2" markerEnd="url(#ah)" />
        <path d="M150 96 C 110 80, 80 70, 60 56" fill="none" stroke="var(--faint)" strokeWidth="2" markerEnd="url(#ah)" />
        <path d="M150 96 C 190 80, 220 70, 240 56" fill="none" stroke="var(--faint)" strokeWidth="2" markerEnd="url(#ah)" />
        <Node x={50} y={40} label="A" />
        <Node x={250} y={40} label="B" />
        <Node x={150} y={100} label="C" />
        <text x="150" y="140" textAnchor="middle" fontSize="12" fill="var(--muted)">
          3 payments
        </text>
      </svg>

      {/* After: one simplified transfer */}
      <svg className="hero-layer hero-b" viewBox="0 0 300 150">
        <defs>
          <marker id="ah2" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="var(--positive)" />
          </marker>
        </defs>
        <path d="M150 92 C 120 70, 80 58, 62 50" fill="none" stroke="var(--positive)" strokeWidth="2.5" markerEnd="url(#ah2)" />
        <Node x={50} y={40} label="A" />
        <Node x={250} y={40} label="B" />
        <Node x={150} y={100} label="C" />
        <g>
          <rect x="104" y="128" width="92" height="20" rx="10" fill="var(--positive-bg)" />
          <text x="150" y="142" textAnchor="middle" fontSize="12" fontWeight="600" fill="var(--positive)">
            1 payment
          </text>
        </g>
      </svg>
    </div>
  );
}
