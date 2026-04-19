import { NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'

import { AdminApplicationsPage, AdminUsersPage } from '../features/admin/AdminPages'
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
import {
  CertificateDetailPage,
  CertificatesPage,
  DashboardPage,
  LearningEnrollmentPage,
  LearningPage,
} from '../features/learning/LearningPages'
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
          </>
        ) : null}
      </nav>

      <div className="app-header__spacer" />

      <div className="app-header__meta">
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
            <Route index element={<NotFoundRedirect />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="learning" element={<LearningPage />} />
            <Route path="learning/:enrollmentId" element={<LearningEnrollmentPage />} />
            <Route path="certificates" element={<CertificatesPage />} />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="catalog" element={<CatalogPage />} />
            <Route path="catalog/:courseId" element={<StudentCoursePage />} />
            <Route path="search" element={<SearchPage />} />
          <Route element={<RoleRoute roles={['instructor', 'admin']} />}>
            <Route path="courses" element={<CourseWorkspacePage />} />
            <Route path="courses/:courseId" element={<CourseEditorPage />} />
          </Route>
          <Route element={<RoleRoute roles={['admin']} />}>
            <Route path="admin/users" element={<AdminUsersPage />} />
            <Route path="admin/instructor-applications" element={<AdminApplicationsPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="/certificates/:certificateId" element={<CertificateDetailPage />} />

      <Route path="*" element={<NotFoundRedirect />} />
    </Routes>
  )
}
