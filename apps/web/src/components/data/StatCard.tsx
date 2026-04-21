import type { ReactNode } from 'react'

interface StatCardProps {
  label: string
  value: ReactNode
  className?: string
}

export function StatCard({ label, value, className = '' }: StatCardProps) {
  return (
    <div className={`stat-item ${className}`}>
      <div className="stat-item__label">{label}</div>
      <div className="stat-item__value">{value}</div>
    </div>
  )
}

export function StatRow({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`stat-row ${className}`}>{children}</div>
}
