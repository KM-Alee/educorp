interface SkeletonProps {
  variant?: 'text' | 'title' | 'card' | 'avatar'
  className?: string
  width?: string
}

export function Skeleton({ variant = 'text', className = '', width }: SkeletonProps) {
  const cls = ['skeleton', `skeleton--${variant}`, className].filter(Boolean).join(' ')
  return <div className={cls} style={width ? { width } : undefined} />
}

export function SkeletonRows({ count = 3 }: { count?: number }) {
  return (
    <div className="flex-col gap-3">
      {Array.from({ length: count }, (_, i) => (
        <Skeleton key={i} variant="text" width={`${60 + Math.random() * 30}%`} />
      ))}
    </div>
  )
}
