import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'

import { PublicLayout } from './layouts/PublicLayout'
import { AuthLayout } from './layouts/AuthLayout'
import { AppShell } from './layouts/AppShell'

import {
  AdminApplicationsPage,
  AdminUsersPage,
  AdminAnalyticsPage,
  AdminWorkflowsPage,
  AdminAuditLogPage,
  AdminDLQPage,
  AdminDashboardPage,
  AdminEnrollmentsPage,
} from '../features/admin/AdminPages'
import {
  ForgotPasswordPage,
  LoginPage,
  RegisterPage,
  ResetPasswordPage,
  VerifyEmailPage,
} from '../features/auth/AuthPages'
import { CatalogPage, SearchPage } from '../features/catalog/CatalogPages'
import { CourseEditorPage, CourseWorkspacePage, InstructorEnrollmentsPage } from '../features/courses/CoursePages'
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
  defaultRouteForSession,
  useSessionState,
} from '../lib/session'

/* -- Route guards -- */

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

function NotFoundRedirect() {
  const session = useSessionState()
  return <Navigate to={session ? defaultRouteForSession(session) : '/'} replace />
}

/* -- Route tree -- */

export function AppRoutes() {
  return (
    <Routes>
      {/* Public pages with top nav */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/catalog" element={<CatalogPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/certificates/:certificateId" element={<CertificateDetailPage />} />
      </Route>

      {/* Auth pages (centered card layout) */}
      <Route element={<PublicOnlyRoute />}>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
        </Route>
      </Route>

      {/* Authenticated app (sidebar + topbar shell) */}
      <Route element={<ProtectedRoute />}>
        <Route path="/app" element={<AppShell />}>
          <Route index element={<NotFoundRedirect />} />

          {/* Student routes */}
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="learning" element={<LearningPage />} />
          <Route path="learning/:enrollmentId" element={<LearningEnrollmentPage />} />
          <Route path="certificates" element={<CertificatesPage />} />

          {/* Shared routes */}
          <Route path="catalog" element={<CatalogPage />} />
          <Route path="catalog/:courseId" element={<StudentCoursePage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="notifications" element={<NotificationsPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="settings" element={<SettingsPage />} />

          {/* Instructor routes */}
          <Route element={<RoleRoute roles={['instructor', 'admin']} />}>
            <Route path="courses" element={<CourseWorkspacePage />} />
            <Route path="courses/:courseId" element={<CourseEditorPage />} />
            <Route path="courses/:courseId/enrollments" element={<InstructorEnrollmentsPage />} />
          </Route>

          {/* Admin routes */}
          <Route element={<RoleRoute roles={['admin']} />}>
            <Route path="admin" element={<AdminDashboardPage />} />
            <Route path="admin/users" element={<AdminUsersPage />} />
            <Route path="admin/instructor-applications" element={<AdminApplicationsPage />} />
            <Route path="admin/enrollments" element={<AdminEnrollmentsPage />} />
            <Route path="admin/analytics" element={<AdminAnalyticsPage />} />
            <Route path="admin/workflows" element={<AdminWorkflowsPage />} />
            <Route path="admin/audit-log" element={<AdminAuditLogPage />} />
            <Route path="admin/dlq" element={<AdminDLQPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundRedirect />} />
    </Routes>
  )
}
