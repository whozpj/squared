import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

// A looping animated "show" that sets up the problem (everyone owes everyone),
// emphasizes the mess, then resolves it to one clean payment with Squared.
// Built with Framer Motion. No gradients; money is the only color.

type P = { x: number; y: number; label: string; tone: "pos" | "neg" };
const PEOPLE: P[] = [
  { x: 120, y: 150, label: "A", tone: "pos" },
  { x: 400, y: 150, label: "B", tone: "pos" },
  { x: 120, y: 320, label: "C", tone: "neg" },
  { x: 400, y: 320, label: "D", tone: "neg" },
];

// Curved path between two points, bent perpendicular by `bend`.
function arc(a: P, b: P, bend: number) {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  const cx = mx + (-dy / len) * bend;
  const cy = my + (dx / len) * bend;
  return `M ${a.x} ${a.y} Q ${cx} ${cy} ${b.x} ${b.y}`;
}

const PAIRS: [number, number, number][] = [
  [0, 1, 40],
  [0, 2, 40],
  [0, 3, 30],
  [1, 2, -30],
  [1, 3, 40],
  [2, 3, 40],
];

const CAPTIONS = [
  { t: "Dinner for four.", s: "One bill, four people, a pile of receipts." },
  { t: "Everyone owes everyone.", s: "Six awkward payments to untangle." },
  { t: "Squared nets it out.", s: "One greedy algorithm, minimum transfers." },
  { t: "Settle in the fewest taps.", s: "6 payments become 2." },
];

export function WelcomeShow() {
  const reduced = useReducedMotion();
  const [phase, setPhase] = useState(reduced ? 3 : 0);

  useEffect(() => {
    if (reduced) return;
    const id = setInterval(() => setPhase((p) => (p + 1) % 4), 2800);
    return () => clearInterval(id);
  }, [reduced]);

  const spring = { type: "spring", stiffness: 260, damping: 20 } as const;

  return (
    <div className="show-stage">
      <svg viewBox="0 0 520 470" className="show-svg" aria-hidden>
        <defs>
          <marker id="mGreen" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="var(--positive)" />
          </marker>
          <marker id="mMess" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L6,3 L0,6 Z" fill="var(--negative)" />
          </marker>
        </defs>

        {/* Phase 0: the bill drops in */}
        <AnimatePresence>
          {phase === 0 && (
            <motion.g
              key="bill"
              initial={{ opacity: 0, y: -160 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.6, y: -40 }}
              transition={spring}
            >
              <rect x="196" y="150" width="128" height="180" rx="12" fill="var(--surface)" stroke="var(--border-strong)" />
              <rect x="216" y="172" width="60" height="9" rx="4" fill="var(--ink)" />
              {[200, 220, 240].map((y) => (
                <g key={y}>
                  <rect x="216" y={y} width="52" height="7" rx="3.5" fill="var(--border-strong)" />
                  <rect x="284" y={y} width="20" height="7" rx="3.5" fill="var(--muted)" />
                </g>
              ))}
              <line x1="216" y1="266" x2="304" y2="266" stroke="var(--border)" />
              <motion.text
                x="260"
                y="300"
                textAnchor="middle"
                fontSize="30"
                fontWeight="800"
                fill="var(--ink)"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ ...spring, delay: 0.25 }}
                style={{ transformBox: "fill-box", transformOrigin: "center" }}
              >
                $83.00
              </motion.text>
            </motion.g>
          )}
        </AnimatePresence>

        {/* People appear from phase 1 on */}
        <AnimatePresence>
          {phase >= 1 && (
            <motion.g key="people" initial="hide" animate="show" exit="hide">
              {PEOPLE.map((p, i) => (
                <motion.g
                  key={p.label}
                  variants={{
                    hide: { opacity: 0, scale: 0 },
                    show: { opacity: 1, scale: 1, transition: { ...spring, delay: 0.06 * i } },
                  }}
                  style={{ transformBox: "fill-box", transformOrigin: "center" }}
                >
                  <circle cx={p.x} cy={p.y} r="34" fill="var(--surface-2)" stroke="var(--border)" />
                  <text x={p.x} y={p.y + 6} textAnchor="middle" fontSize="17" fontWeight="700" fill="var(--muted)">
                    {p.label}
                  </text>
                </motion.g>
              ))}
            </motion.g>
          )}
        </AnimatePresence>

        {/* Phase 1: the tangle of payments (the problem), with a jitter */}
        <AnimatePresence>
          {phase === 1 && (
            <motion.g
              key="mess"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1, x: [0, -2.5, 2.5, -1.5, 1.5, 0] }}
              exit={{ opacity: 0 }}
              transition={{ opacity: { duration: 0.3 }, x: { duration: 0.5, repeat: Infinity, repeatDelay: 0.6 } }}
            >
              {PAIRS.map(([a, b, bend], i) => (
                <motion.path
                  key={i}
                  d={arc(PEOPLE[a], PEOPLE[b], bend)}
                  fill="none"
                  stroke="var(--negative)"
                  strokeWidth="2"
                  strokeOpacity="0.55"
                  markerEnd="url(#mMess)"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.5, delay: 0.1 + i * 0.09 }}
                />
              ))}
              <motion.g
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: [0, 1.15, 1], opacity: 1 }}
                transition={{ delay: 0.7, duration: 0.5 }}
                style={{ transformBox: "fill-box", transformOrigin: "center" }}
              >
                <rect x="205" y="222" width="110" height="34" rx="17" fill="var(--negative-bg)" />
                <text x="260" y="245" textAnchor="middle" fontSize="16" fontWeight="800" fill="var(--negative)">
                  6 payments?!
                </text>
              </motion.g>
            </motion.g>
          )}
        </AnimatePresence>

        {/* Phase 2: Squared steps in */}
        <AnimatePresence>
          {phase === 2 && (
            <motion.g key="squared" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <motion.circle
                cx="260"
                cy="235"
                r="70"
                fill="none"
                stroke="var(--ink)"
                strokeWidth="2"
                initial={{ scale: 0.2, opacity: 0.6 }}
                animate={{ scale: 1.8, opacity: 0 }}
                transition={{ duration: 1.1, repeat: Infinity }}
                style={{ transformBox: "fill-box", transformOrigin: "center" }}
              />
              <motion.rect
                x="234"
                y="209"
                width="52"
                height="52"
                rx="14"
                fill="var(--ink)"
                initial={{ scale: 0, rotate: -30 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={spring}
                style={{ transformBox: "fill-box", transformOrigin: "center" }}
              />
              <rect x="248" y="223" width="24" height="24" rx="6" fill="none" stroke="var(--paper)" strokeWidth="3" />
            </motion.g>
          )}
        </AnimatePresence>

        {/* Phase 3: one clean payment + badge */}
        <AnimatePresence>
          {phase === 3 && (
            <motion.g key="solved" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              {[
                arc(PEOPLE[2], PEOPLE[0], 30),
                arc(PEOPLE[3], PEOPLE[1], 30),
              ].map((d, i) => (
                <motion.path
                  key={i}
                  d={d}
                  fill="none"
                  stroke="var(--positive)"
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  markerEnd="url(#mGreen)"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.6, delay: 0.15 + i * 0.2 }}
                />
              ))}
              <motion.g
                initial={{ scale: 0, y: 8 }}
                animate={{ scale: 1, y: 0 }}
                transition={{ ...spring, delay: 0.5 }}
                style={{ transformBox: "fill-box", transformOrigin: "center" }}
              >
                <rect x="168" y="218" width="184" height="36" rx="18" fill="var(--positive-bg)" />
                <text x="260" y="242" textAnchor="middle" fontSize="16" fontWeight="800" fill="var(--positive)">
                  6 → 2 payments
                </text>
              </motion.g>
            </motion.g>
          )}
        </AnimatePresence>
      </svg>

      <div className="show-caption">
        <AnimatePresence mode="wait">
          <motion.div
            key={phase}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.35 }}
          >
            <div className="show-cap-title">{CAPTIONS[phase].t}</div>
            <div className="show-cap-sub">{CAPTIONS[phase].s}</div>
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="hero-dots">
        {[0, 1, 2, 3].map((i) => (
          <span key={i} className={`hero-dot ${i === phase ? "on" : ""}`} />
        ))}
      </div>
    </div>
  );
}
