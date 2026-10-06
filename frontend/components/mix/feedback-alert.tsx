/** Full-width live warning. Never hidden behind other UI (Design-Art 4.3). */
export function FeedbackAlert({ freqHz, onDismiss }: { freqHz: number; onDismiss: () => void }) {
  return (
    <div className="feedback-alert" role="alert">
      <span className="label">Feedback</span>
      <span>
        <span className="freq">{Math.round(freqHz)} Hz</span>
        <span className="meta"> — growing tone detected. Suggested notch −4 dB, Q 10.</span>
      </span>
      <button className="btn" type="button" onClick={onDismiss}>
        Dismiss
      </button>
    </div>
  );
}
