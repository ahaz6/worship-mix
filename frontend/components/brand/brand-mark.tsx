/**
 * Worship Suite brand anchor: round product logo + two-line wordmark
 * (Design-Art.md 3.1). Worship Mix has no final logo yet, so a neutral
 * round emblem stands in. TODO: replace with the real "Worship Mix Icon.png"
 * via next/image exactly like Worship Keys' BrandMark.
 */
export function BrandMark({ size = 48 }: { size?: number }) {
  return (
    <div className="brand">
      <span className="brand-logo brand-logo-placeholder" style={{ width: size, height: size, flexBasis: size }} aria-hidden="true">
        <svg viewBox="0 0 48 48" width={size * 0.56} height={size * 0.56}>
          {[10, 18, 26, 34].map((x, i) => (
            <g key={x}>
              <line x1={x} y1="8" x2={x} y2="40" stroke="#3a3550" strokeWidth="2" strokeLinecap="round" />
              <rect x={x - 4} y={[26, 14, 20, 30][i]} width="8" height="5" rx="2" fill={i === 1 ? "#9d8cff" : "#b5b3c1"} />
            </g>
          ))}
        </svg>
      </span>
      <span className="brand-copy">
        <b>Worship</b>
        <strong>Mix</strong>
      </span>
    </div>
  );
}
