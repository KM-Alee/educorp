interface ProgressBarProps {
  value: number
  max?: number
  variant?: 'default' | 'success'
  className?: string
}

export function ProgressBar({ value, max = 100, variant = 'default', className = '' }: ProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  const cls = ['progress-bar', variant === 'success' ? 'progress-bar--success' : '', className]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={cls} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={max}>
      <div className="progress-bar__fill" style={{ width: `${pct}%` }} />
    </div>
  )
}
