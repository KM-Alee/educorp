interface AvatarProps {
  name?: string
  src?: string | null
  size?: 'default' | 'lg'
  className?: string
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  }
  return name.slice(0, 2).toUpperCase()
}

export function Avatar({ name, src, size = 'default', className = '' }: AvatarProps) {
  const cls = ['avatar', size === 'lg' ? 'avatar--lg' : '', className]
    .filter(Boolean)
    .join(' ')

  if (src) {
    return (
      <div className={cls}>
        <img src={src} alt={name ?? 'User avatar'} />
      </div>
    )
  }

  return <div className={cls}>{name ? getInitials(name) : '?'}</div>
}
