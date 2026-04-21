import type { ReactNode } from 'react'

interface TimelineItem {
  title: string
  meta?: string
  status?: 'active' | 'success' | 'error'
  children?: ReactNode
}

interface TimelineProps {
  items: TimelineItem[]
}

export function Timeline({ items }: TimelineProps) {
  return (
    <div className="timeline">
      {items.map((item, i) => {
        const statusCls = item.status ? `timeline__item--${item.status}` : ''
        return (
          <div key={i} className={`timeline__item ${statusCls}`}>
            <div className="timeline__title">{item.title}</div>
            {item.meta ? <div className="timeline__meta">{item.meta}</div> : null}
            {item.children}
          </div>
        )
      })}
    </div>
  )
}
