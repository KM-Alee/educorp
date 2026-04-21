import type { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  clickable?: boolean
  onClick?: () => void
}

export function Card({ children, className = '', clickable, onClick }: CardProps) {
  const cls = ['card', clickable ? 'card--clickable' : '', className]
    .filter(Boolean)
    .join(' ')

  return (
    <div className={cls} onClick={onClick} role={clickable ? 'button' : undefined} tabIndex={clickable ? 0 : undefined}>
      {children}
    </div>
  )
}

export function CardHeader({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children?: ReactNode
}) {
  return (
    <div className="card__header">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="card__title">{title}</h2>
          {description ? <p className="card__description">{description}</p> : null}
        </div>
        {children}
      </div>
    </div>
  )
}
