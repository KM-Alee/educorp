import type { ReactNode } from 'react'

type BadgeVariant = 'default' | 'success' | 'danger' | 'warning' | 'info'

interface BadgeProps {
  variant?: BadgeVariant
  children: ReactNode
  className?: string
}

export function Badge({ variant = 'default', children, className = '' }: BadgeProps) {
  const cls = ['badge', variant !== 'default' ? `badge--${variant}` : '', className]
    .filter(Boolean)
    .join(' ')

  return <span className={cls}>{children}</span>
}
