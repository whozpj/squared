import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

// A fast, looping animated "show": the bill → everyone owes everyone (the mess)
// → Squared nets it out → the fewest payments. Framer Motion, no gradients.

type Pt = { x: number; y: number };
type Person = Pt & { label: string };

const PEOPLE: Person[] = [
  { x: 120, y: 150, label: "A" },
  { x: 400, y: 150, label: "B" },
  { x: 120, y: 320, label: "C" },
  { x: 400, y: 320, label: "D" },
];
const CENTER: Pt = { x: 260, y: 235 };
const PHASE_MS = 1800;

function control(a: Pt, b: Pt, bend: number): Pt {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  return { x: (a.x + b.x) / 2 + (-dy / len) * bend, y: (a.y + b.y) / 2 + (dx / len) * bend };
}
function arcPath(a: Pt, b: Pt, bend: number) {
  const c = control(a, b, bend);
  return `M ${a.x} ${a.y} Q ${c.x} ${c.y} ${b.x} ${b.y}`;
}
// Points along the quadratic curve, for coins to travel on.
function sample(a: Pt, b: Pt, bend: number, n = 12): Pt[] {
  const c = control(a, b, bend);
  return Array.from({ length: n + 1 }, (_, i) => {
    const t = i / n;
    const u = 1 - t;
    return { x: u * u * a.x + 2 * u * t * c.x + t * t * b.x, y: u * u * a.y + 2 * u * t * c.y + t * t * b.y };
  });
}

const PAIRS: [number, number, number][] = [
  [0, 1, 40],
  [0, 2, 40],
  [0, 3, 30],
  [1, 2, -30],
  [1, 3, 40],
  [2, 3, 40],
];
const SOLVED: [number, number, number][] = [
  [2, 0, 30],
  [3, 1, 30],
];

const CAPTIONS = [
  { t: "Dinner for four.", s: "One $83 bill. Who owes what?" },
  { t: "Everyone owes everyone.", s: "Six awkward payments flying around." },
  { t: "Squared nets it out.", s: "A greedy algorithm finds the minimum." },
  { t: "Two taps. Done.", s: "6 payments become 2." },
];

const spring = { type: "spring", stiffness: 420, damping: 22 } as const;

function Coin({ path, color, delay }: { path: Pt[]; color: string; delay: number }) {
  return (
    <motion.g
      initial={{ x: path[0].x, y: path[0].y, opacity: 0 }}
      animate={{ x: path.map((p) => p.x), y: path.map((p) => p.y), opacity: [0, 1, 1, 0] }}
      transition={{ duration: 0.9, delay, repeat: Infinity, repeatDelay: 0.15, ease: "easeInOut" }}
    >
      <circle r="10" fill={color} />
      <text y="4" textAnchor="middle" fontSize="11" fontWeight="800" fill="#fff">
        $
      </text>
    </motion.g>
  );
}

// Little squares bursting out on the win.
const BURST = Array.from({ length: 14 }, (_, i) => {
  const ang = (i / 14) * Math.PI * 2;
  const dist = 90 + (i % 3) * 26;
  const colors = ["var(--positive)", "var(--ink)", "var(--negative)", "var(--border-strong)"];
  return { dx: Math.cos(ang) * dist, dy: Math.sin(ang) * dist, rot: i * 47, c: colors[i % colors.length] };
});

export function WelcomeShow() {
  const reduced = useReducedMotion();
  const [phase, setPhase] = useState(reduced ? 3 : 0);

  useEffect(() => {
    if (reduced) return;
    const id = setInterval(() => setPhase((p) => (p + 1) % 4), PHASE_MS);
    return () => clearInterval(id);
  }, [reduced]);

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

        {/* Phase 0: the bill drops in and gets scanned */}
        <AnimatePresence>
          {phase === 0 && (
            <motion.g
              key="bill"
              initial={{ opacity: 0, y: -180, rotate: -8 }}
              animate={{ opacity: 1, y: 0, rotate: 0 }}
              exit={{ opacity: 0, scale: 0.3, y: 0, transition: { duration: 0.25 } }}
              transition={{ ...spring, delay: 0.15 }}
              style={{ transformBox: "fill-box", transformOrigin: "center" }}
            >
              <rect x="190" y="130" width="140" height="200" rx="14" fill="var(--surface)" stroke="var(--border-strong)" strokeWidth="1.5" />
              <rect x="210" y="152" width="70" height="10" rx="5" fill="var(--ink)" />
              {[182, 204, 226, 248].map((y, i) => (
                <motion.g
                  key={y}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.15 + i * 0.08, duration: 0.25 }}
                >
                  <rect x="210" y={y} width="62" height="8" rx="4" fill="var(--border-strong)" />
                  <rect x="286" y={y} width="24" height="8" rx="4" fill="var(--muted)" />
                </motion.g>
              ))}
              <line x1="210" y1="274" x2="310" y2="274" stroke="var(--border)" />
              <motion.text
                x="260"
                y="310"
                textAnchor="middle"
                fontSize="32"
                fontWeight="800"
                fill="var(--ink)"
                initial={{ scale: 0 }}
                animate={{ scale: [0, 1.25, 1] }}
                transition={{ delay: 0.5, duration: 0.35 }}
                style={{ transformBox: "fill-box", transformOrigin: "center" }}
              >
                $83.00
              </motion.text>
              {/* scan line */}
              <motion.rect
                x="194"
                width="132"
                height="5"
                rx="2.5"
                fill="var(--positive)"
                initial={{ y: 138, opacity: 0 }}
                animate={{ y: [138, 320], opacity: [0, 0.85, 0.85, 0] }}
                transition={{ duration: 0.9, repeat: Infinity, ease: "easeInOut" }}
              />
            </motion.g>
          )}
        </AnimatePresence>

        {/* People, from phase 1 on — they jitter in the mess and bounce on the win */}
        <AnimatePresence>
          {phase >= 1 && (
            <motion.g key="people" initial="hide" animate="show" exit="hide">
              {PEOPLE.map((p, i) => (
                <motion.g
                  key={p.label}
                  variants={{
                    hide: { opacity: 0, scale: 0, transition: { duration: 0.15 } },
                    show: { opacity: 1, scale: 1, transition: { ...spring, delay: 0.04 * i } },
                  }}
                  style={{ transformBox: "fill-box", transformOrigin: "center" }}
                >
                  <motion.g
                    animate={
                      phase === 1
                        ? { x: [0, -3, 3, -2, 2, 0], rotate: [0, -4, 4, 0] }
                        : phase === 3
                          ? { y: [0, -12, 0] }
                          : { x: 0, y: 0, rotate: 0 }
                    }
                    transition={
                      phase === 1
                        ? { duration: 0.4, repeat: Infinity, delay: i * 0.05 }
                        : { duration: 0.45, delay: 0.5 + i * 0.07 }
                    }
                    style={{ transformBox: "fill-box", transformOrigin: "center" }}
                  >
                    <circle cx={p.x} cy={p.y} r="34" fill="var(--surface-2)" stroke="var(--border-strong)" strokeWidth="1.5" />
                    <text x={p.x} y={p.y + 6} textAnchor="middle" fontSize="18" fontWeight="800" fill="var(--ink)">
                      {p.label}
                    </text>
                  </motion.g>
                </motion.g>
              ))}
            </motion.g>
          )}
        </AnimatePresence>

        {/* Phase 1: the tangle — six arrows, red coins flying everywhere */}
        <AnimatePresence>
          {phase === 1 && (
            <motion.g key="mess" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.2 } }}>
              {PAIRS.map(([a, b, bend], i) => (
                <motion.path
                  key={i}
                  d={arcPath(PEOPLE[a], PEOPLE[b], bend)}
                  fill="none"
                  stroke="var(--negative)"
                  strokeWidth="2.5"
                  strokeOpacity="0.6"
                  markerEnd="url(#mMess)"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.3, delay: i * 0.05 }}
                />
              ))}
              {PAIRS.map(([a, b, bend], i) => (
                <Coin key={`c${i}`} path={sample(PEOPLE[a], PEOPLE[b], bend)} color="var(--negative)" delay={0.2 + i * 0.1} />
              ))}
              <motion.g
                initial={{ scale: 0 }}
                animate={{ scale: [0, 1.3, 1, 1.08, 1] }}
                transition={{ delay: 0.35, duration: 0.8, repeat: Infinity, repeatDelay: 0.2 }}
                style={{ transformBox: "fill-box", transformOrigin: "center" }}
              >
                <rect x="196" y="217" width="128" height="38" rx="19" fill="var(--negative)" />
                <text x="260" y="242" textAnchor="middle" fontSize="17" fontWeight="800" fill="#fff">
                  6 payments?!
                </text>
              </motion.g>
            </motion.g>
          )}
        </AnimatePresence>

        {/* Phase 2: Squared sucks the mess in */}
        <AnimatePresence>
          {phase === 2 && (
            <motion.g key="squared" initial={{ opacity: 1 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.2 } }}>
              {PAIRS.map(([a, b, bend], i) => (
                <motion.path
                  key={i}
                  d={arcPath(PEOPLE[a], PEOPLE[b], bend)}
                  fill="none"
                  stroke="var(--negative)"
                  strokeWidth="2.5"
                  initial={{ opacity: 0.6, scale: 1 }}
                  animate={{ opacity: 0, scale: 0.1 }}
                  transition={{ duration: 0.45, ease: "easeIn" }}
                  style={{ transformOrigin: `${CENTER.x}px ${CENTER.y}px` }}
                />
              ))}
              {[0, 0.3, 0.6].map((d) => (
                <motion.circle
                  key={d}
                  cx={CENTER.x}
                  cy={CENTER.y}
                  r="60"
                  fill="none"
                  stroke="var(--ink)"
                  strokeWidth="2"
                  initial={{ scale: 0.3, opacity: 0.7 }}
                  animate={{ scale: 2.4, opacity: 0 }}
                  transition={{ duration: 0.9, delay: d, repeat: Infinity }}
                  style={{ transformBox: "fill-box", transformOrigin: "center" }}
                />
              ))}
              <motion.g
                initial={{ scale: 0, rotate: -90 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ ...spring, delay: 0.15 }}
                style={{ transformBox: "fill-box", transformOrigin: "center" }}
              >
                <rect x={CENTER.x - 32} y={CENTER.y - 32} width="64" height="64" rx="16" fill="var(--ink)" />
                <rect x={CENTER.x - 15} y={CENTER.y - 15} width="30" height="30" rx="7" fill="none" stroke="var(--paper)" strokeWidth="3.5" />
              </motion.g>
            </motion.g>
          )}
        </AnimatePresence>

        {/* Phase 3: two clean payments, green coins, confetti */}
        <AnimatePresence>
          {phase === 3 && (
            <motion.g key="solved" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, transition: { duration: 0.2 } }}>
              {SOLVED.map(([a, b, bend], i) => (
                <motion.path
                  key={i}
                  d={arcPath(PEOPLE[a], PEOPLE[b], bend)}
                  fill="none"
                  stroke="var(--positive)"
                  strokeWidth="4.5"
                  strokeLinecap="round"
                  markerEnd="url(#mGreen)"
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ duration: 0.35, delay: i * 0.1 }}
                />
              ))}
              {SOLVED.map(([a, b, bend], i) => (
                <Coin key={`g${i}`} path={sample(PEOPLE[a], PEOPLE[b], bend)} color="var(--positive)" delay={0.3 + i * 0.15} />
              ))}
              {BURST.map((b, i) => (
                <motion.rect
                  key={i}
                  x={CENTER.x - 5}
                  y={CENTER.y - 5}
                  width="10"
                  height="10"
                  rx="2.5"
                  fill={b.c}
                  initial={{ x: 0, y: 0, opacity: 0, rotate: 0, scale: 0.4 }}
                  animate={{ x: b.dx, y: b.dy, opacity: [0, 1, 0], rotate: b.rot, scale: 1 }}
                  transition={{ duration: 0.8, delay: 0.3, ease: "easeOut" }}
                />
              ))}
              <motion.g
                initial={{ scale: 0 }}
                animate={{ scale: [0, 1.25, 1] }}
                transition={{ delay: 0.25, duration: 0.4 }}
                style={{ transformBox: "fill-box", transformOrigin: "center" }}
              >
                <rect x="160" y="215" width="200" height="42" rx="21" fill="var(--positive)" />
                <text x="260" y="242" textAnchor="middle" fontSize="18" fontWeight="800" fill="#fff">
                  6 → 2 payments ✓
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
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.2 }}
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

// Floating outlined squares drifting across the whole screen, behind the show.
const SQUARES = [
  { l: 6, t: 18, s: 44, d: 9, f: false },
  { l: 14, t: 70, s: 28, d: 7, f: true },
  { l: 24, t: 40, s: 18, d: 6, f: false },
  { l: 82, t: 22, s: 36, d: 8, f: true },
  { l: 90, t: 62, s: 52, d: 10, f: false },
  { l: 72, t: 82, s: 24, d: 7, f: false },
  { l: 40, t: 88, s: 34, d: 9, f: true },
  { l: 58, t: 12, s: 20, d: 6, f: false },
  { l: 4, t: 48, s: 22, d: 8, f: true },
  { l: 95, t: 40, s: 18, d: 6, f: false },
];

export function FloatingSquares() {
  const reduced = useReducedMotion();
  return (
    <div className="welcome-bg" aria-hidden>
      {SQUARES.map((q, i) => (
        <motion.div
          key={i}
          className={`float-sq${q.f ? " filled" : ""}`}
          style={{ left: `${q.l}%`, top: `${q.t}%`, width: q.s, height: q.s }}
          animate={reduced ? undefined : { y: [0, -24, 0], rotate: [0, 18, 0] }}
          transition={{ duration: q.d, repeat: Infinity, ease: "easeInOut", delay: i * 0.4 }}
        />
      ))}
    </div>
  );
}
