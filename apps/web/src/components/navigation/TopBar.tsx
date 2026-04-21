import { Link, useNavigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { Bell, LogOut, Search } from 'lucide-react'

import { Avatar } from '../ui/Avatar'
import { clearSession, type SessionState } from '../../lib/session'

interface TopBarProps {
  session?: SessionState | null
  children?: ReactNode
}

export function TopBar({ session, children }: TopBarProps) {
  const navigate = useNavigate()

  return (
    <header className="topbar">
      {children}
      <div className="topbar__search">
        <Search size={15} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--black-faint)', pointerEvents: 'none' }} />
        <input type="text" placeholder="Search courses, enrollments..." readOnly onClick={() => navigate('/app/search')} />
      </div>
      <div className="topbar__spacer" />
      <div className="topbar__actions">
        {session ? (
          <>
            <Link to="/app/notifications" className="btn btn--ghost btn--icon btn--sm" title="Notifications">
              <Bell size={18} />
            </Link>
            <Link to="/app/profile" className="topbar__user" style={{ textDecoration: 'none' }}>
              <Avatar name={session.user.email} size="default" />
              <span>{session.user.email}</span>
            </Link>
            <button
              className="btn btn--ghost btn--sm"
              onClick={() => {
                clearSession()
                navigate('/login', { replace: true })
              }}
              type="button"
              title="Log out"
            >
              <LogOut size={16} />
            </button>
          </>
        ) : null}
      </div>
    </header>
  )
}
