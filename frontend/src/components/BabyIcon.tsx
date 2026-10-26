/** Original line-art baby face: closed smiling eyes, rosy cheeks. Bow for a girl, a curl for a boy. */
export function BabyIcon({ type, size = 56 }: { type: "girl" | "boy"; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label={type === "girl" ? "Baby girl" : "Baby boy"}>
      <circle cx="32" cy="35" r="22" fill="var(--surface)" stroke="var(--ink)" strokeWidth="2.2" />
      <circle cx="21" cy="40" r="4.2" fill="var(--pink-200)" />
      <circle cx="43" cy="40" r="4.2" fill="var(--pink-200)" />
      <path d="M21 33 q3 3 6 0" fill="none" stroke="var(--ink)" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M37 33 q3 3 6 0" fill="none" stroke="var(--ink)" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M28 44 q4 3.5 8 0" fill="none" stroke="var(--ink)" strokeWidth="2.2" strokeLinecap="round" />
      {type === "girl" ? (
        <g>
          <path d="M32 13 L23 8 Q20 13 23 18 Z" fill="var(--pink-200)" stroke="var(--ink)" strokeWidth="2" strokeLinejoin="round" />
          <path d="M32 13 L41 8 Q44 13 41 18 Z" fill="var(--pink-200)" stroke="var(--ink)" strokeWidth="2" strokeLinejoin="round" />
          <circle cx="32" cy="13" r="3" fill="var(--pink-400)" stroke="var(--ink)" strokeWidth="2" />
        </g>
      ) : (
        <path d="M30 14 q-2 -6 4 -7 q5 0 3 5 q-1 3 -4 1" fill="none" stroke="var(--ink)" strokeWidth="2.2" strokeLinecap="round" />
      )}
    </svg>
  );
}

export function Logo({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <circle cx="16" cy="16" r="15" fill="var(--pink-100)" />
      <path d="M8 18c3 5 13 5 16 0" stroke="var(--rose-600)" strokeWidth="2.6" fill="none" strokeLinecap="round" />
      <path d="M11 11.5 q1.5 -2 3 0 M18 11.5 q1.5 -2 3 0" stroke="var(--rose-600)" strokeWidth="2.2" fill="none" strokeLinecap="round" />
    </svg>
  );
}
