import { useCallback, useEffect, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'

import { useSessionState, defaultRouteForSession } from '../../lib/session'

export function PublicLayout() {
  const session = useSessionState()
  const location = useLocation()
  const isHome = location.pathname === '/'
  const [scrolled, setScrolled] = useState(false)

  const handleScroll = useCallback(() => {
    setScrolled(window.scrollY > 20)
  }, [])

  useEffect(() => {
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [handleScroll])

  const navClass = [
    'public-nav',
    scrolled ? 'public-nav--scrolled' : '',
  ].filter(Boolean).join(' ')

  return (
    <div className={`public-layout${isHome ? ' public-layout--home' : ''}`}>
      <nav className={navClass}>
        <div className="public-nav__brand">
          <Link to="/">EduCorp</Link>
        </div>
        <div className="public-nav__spacer" />
        <div className="public-nav__links">
          <Link className="public-nav__link" to="/catalog">
            Catalog
          </Link>
          <Link className="public-nav__link" to="/search">
            Search
          </Link>
          {session ? (
            <Link className="btn btn--primary btn--sm" to={defaultRouteForSession(session)}>
              Dashboard
            </Link>
          ) : (
            <>
              <Link className="public-nav__link" to="/login">
                Sign in
              </Link>
              <Link className="btn btn--primary btn--sm" to="/register">
                Get started
              </Link>
            </>
          )}
        </div>
      </nav>
      <Outlet />
    </div>
  )
}
