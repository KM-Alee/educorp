import { useCallback, useEffect, useState } from 'react'

import { NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate, Link } from 'react-router-dom'

import { AdminApplicationsPage, AdminUsersPage, AdminAnalyticsPage, AdminWorkflowsPage, AdminAuditLogPage, AdminDLQPage } from '../features/admin/AdminPages'
import {
  ForgotPasswordPage,
  LoginPage,
  RegisterPage,
  ResetPasswordPage,
  VerifyEmailPage,
} from '../features/auth/AuthPages'
import { CatalogPage, SearchPage } from '../features/catalog/CatalogPages'
import { CourseEditorPage, CourseWorkspacePage } from '../features/courses/CoursePages'
import { StudentCoursePage } from '../features/courses/StudentCoursePage'
import { HomePage } from '../features/home/HomePage'
import {
  CertificateDetailPage,
  CertificatesPage,
  DashboardPage,
  LearningEnrollmentPage,
  LearningPage,
} from '../features/learning/LearningPages'
import { NotificationsPage } from '../features/notifications/NotificationsPage'
import { ProfilePage } from '../features/profile/ProfilePage'
import { SettingsPage } from '../features/settings/SettingsPage'
import {
  clearSession,
  defaultRouteForSession,
  type SessionState,
  useSessionState,
} from '../lib/session'

/* ── Route guards ─────────────────────────────────────────────── */

function ProtectedRoute() {
  const session = useSessionState()
  const location = useLocation()

  if (!session) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}

function PublicOnlyRoute() {
  const session = useSessionState()

  if (session) {
    return <Navigate to={defaultRouteForSession(session)} replace />
  }

  return <Outlet />
}

function RoleRoute({ roles }: { roles: string[] }) {
  const session = useSessionState()

  if (!session) {
    return <Navigate to="/login" replace />
  }

  if (!roles.some((role) => session.user.roles.includes(role))) {
    return <Navigate to="/app/profile" replace />
  }

  return <Outlet />
}

/* ── Public layout — transparent nav over dark background ──────── */

function PublicNav() {
  const session = useSessionState()
  const [scrolled, setScrolled] = useState(false)

  const handleScroll = useCallback(() => {
    setScrolled(window.scrollY > 20)
  }, [])

  useEffect(() => {
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [handleScroll])

  return (
    <nav className={`public-nav${scrolled ? ' public-nav--scrolled' : ''}`}>
      <div className="public-nav__brand">
        <Link to="/">EduCorp</Link>
      </div>
      <div className="public-nav__spacer" />
      <div className="public-nav__links">
        <Link className="public-nav__link" to="/catalog">Catalog</Link>
        <Link className="public-nav__link" to="/search">Search</Link>
        {session ? (
          <Link className="btn btn--primary btn--sm" to={defaultRouteForSession(session)}>
            Dashboard
          </Link>
        ) : (
          <>
            <Link className="public-nav__link" to="/login">Sign in</Link>
            <Link className="btn btn--primary btn--sm" to="/register">Get started</Link>
          </>
        )}
      </div>
    </nav>
  )
}

function PublicLayout() {
  return (
    <div className="public-layout">
      <PublicNav />
      <Outlet />
    </div>
  )
}

/* ── App shell header — dark nav with role-aware links ─────────── */

function AppShellHeader({ session }: { session: SessionState }) {
  const navigate = useNavigate()

  const isInstructorOrAdmin =
    session.user.roles.includes('instructor') || session.user.roles.includes('admin')
  const isAdmin = session.user.roles.includes('admin')
  const isStudentOnly = session.user.roles.includes('student') && !isInstructorOrAdmin

  return (
    <header className="app-header">
      <div className="app-header__brand">
        <NavLink to={defaultRouteForSession(session)}>EduCorp</NavLink>
      </div>

      <nav className="app-header__nav" aria-label="Primary navigation">
        {isStudentOnly ? (
          <>
            <NavLink className="app-header__link" to="/app/dashboard">
              Dashboard
            </NavLink>
            <NavLink className="app-header__link" to="/app/learning">
              My Learning
            </NavLink>
            <NavLink className="app-header__link" to="/app/certificates">
              Certificates
            </NavLink>
          </>
        ) : null}
        {isInstructorOrAdmin ? (
          <NavLink className="app-header__link" to="/app/courses">
            Courses
          </NavLink>
        ) : null}
        <NavLink className="app-header__link" to="/app/catalog">
          Catalog
        </NavLink>
        <NavLink className="app-header__link" to="/app/search">
          Search
        </NavLink>
        <NavLink className="app-header__link" to="/app/profile">
          Profile
        </NavLink>
        {isAdmin ? (
          <>
            <NavLink className="app-header__link" to="/app/admin/users">
              Users
            </NavLink>
            <NavLink className="app-header__link" to="/app/admin/instructor-applications">
              Applications
            </NavLink>
            <NavLink className="app-header__link" to="/app/admin/analytics">
              Analytics
            </NavLink>
          </>
        ) : null}
      </nav>

      <div className="app-header__spacer" />

      <div className="app-header__meta">
        <NavLink className="app-header__link" to="/app/notifications" title="Notifications">
          &#128276;
        </NavLink>
        <NavLink className="app-header__link" to="/app/settings" title="Settings">
          &#9881;
        </NavLink>
        <div className="app-header__roles">
          {session.user.roles.map((role) => (
            <span className="badge" key={role}>
              {role}
            </span>
          ))}
        </div>
        <span>{session.user.email}</span>
        <button
          className="btn btn--ghost btn--sm"
          onClick={() => {
            clearSession()
            navigate('/login', { replace: true })
          }}
          type="button"
        >
          Log out
        </button>
      </div>
    </header>
  )
}

function AppShell() {
  const session = useSessionState()

  if (!session) {
    return null
  }

  return (
    <div className="app-shell">
      <AppShellHeader session={session} />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  )
}

function NotFoundRedirect() {
  const session = useSessionState()
  return <Navigate to={session ? defaultRouteForSession(session) : '/'} replace />
}

/* ── Route tree ────────────────────────────────────────────────── */

export function AppRoutes() {
  return (
    <Routes>
      {/* Public pages with transparent nav */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/catalog" element={<CatalogPage />} />
        <Route path="/search" element={<SearchPage />} />
      </Route>

      {/* Auth pages (no nav, centered cards) */}
      <Route element={<PublicOnlyRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Route>

      {/* Authenticated app */}
      <Route element={<ProtectedRoute />}>
        <Route path="/app" element={<AppShell />}>
          <Route index element={<NotFoundRedirect />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="learning" element={<LearningPage />} />
          <Route path="learning/:enrollmentId" element={<LearningEnrollmentPage />} />
          <Route path="certificates" element={<CertificatesPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="catalog" element={<CatalogPage />} />
          <Route path="catalog/:courseId" element={<StudentCoursePage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
          <Route path="settings" element={<SettingsPage />} />

          <Route element={<RoleRoute roles={['instructor', 'admin']} />}>
            <Route path="courses" element={<CourseWorkspacePage />} />
            <Route path="courses/:courseId" element={<CourseEditorPage />} />
          </Route>

          <Route element={<RoleRoute roles={['admin']} />}>
            <Route path="admin/users" element={<AdminUsersPage />} />
            <Route path="admin/instructor-applications" element={<AdminApplicationsPage />} />
            <Route path="admin/analytics" element={<AdminAnalyticsPage />} />
            <Route path="admin/workflows" element={<AdminWorkflowsPage />} />
            <Route path="admin/audit-log" element={<AdminAuditLogPage />} />
            <Route path="admin/dlq" element={<AdminDLQPage />} />
          </Route>
        </Route>
      </Route>

      {/* Public certificate detail (shareable link) */}
      <Route element={<PublicLayout />}>
        <Route path="/certificates/:certificateId" element={<CertificateDetailPage />} />
      </Route>

      <Route path="*" element={<NotFoundRedirect />} />
    </Routes>
  )
}
