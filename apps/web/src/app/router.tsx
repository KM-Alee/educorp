import { NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'

import { AdminApplicationsPage, AdminUsersPage } from '../features/admin/AdminPages'
import {
  ForgotPasswordPage,
  LoginPage,
  RegisterPage,
  ResetPasswordPage,
  VerifyEmailPage,
} from '../features/auth/AuthPages'
import { ProfilePage } from '../features/profile/ProfilePage'
import {
  clearSession,
  defaultRouteForSession,
  type SessionState,
  useSessionState,
} from '../lib/session'

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

function RoleRoute({ role }: { role: string }) {
  const session = useSessionState()

  if (!session) {
    return <Navigate to="/login" replace />
  }

  if (!session.user.roles.includes(role)) {
    return <Navigate to="/app/profile" replace />
  }

  return <Outlet />
}

function AppShellHeader({ session }: { session: SessionState }) {
  const navigate = useNavigate()

  return (
    <header className="shell-header">
      <div className="shell-brand">
        <strong>
          <NavLink to={defaultRouteForSession(session)}>EduCorp Phase 1</NavLink>
        </strong>
        <span>{session.user.email}</span>
      </div>

      <nav className="shell-nav" aria-label="Primary navigation">
        <NavLink className="nav-link" to="/app/profile">
          Profile
        </NavLink>
        {session.user.roles.includes('admin') ? (
          <>
            <NavLink className="nav-link" to="/app/admin/users">
              Users
            </NavLink>
            <NavLink className="nav-link" to="/app/admin/instructor-applications">
              Instructor Queue
            </NavLink>
          </>
        ) : null}
      </nav>

      <div className="page-actions">
        <div className="role-list">
          {session.user.roles.map((role) => (
            <span className="pill" key={role}>
              {role}
            </span>
          ))}
        </div>
        <button
          className="button button--ghost"
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
    <div className="shell page">
      <AppShellHeader session={session} />
      <main className="shell-main">
        <Outlet />
      </main>
    </div>
  )
}

function NotFoundRedirect() {
  const session = useSessionState()
  return <Navigate to={session ? defaultRouteForSession(session) : '/login'} replace />
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicOnlyRoute />}>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route path="/app" element={<AppShell />}>
          <Route index element={<Navigate to="/app/profile" replace />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route element={<RoleRoute role="admin" />}>
            <Route path="admin/users" element={<AdminUsersPage />} />
            <Route path="admin/instructor-applications" element={<AdminApplicationsPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundRedirect />} />
    </Routes>
  )
}