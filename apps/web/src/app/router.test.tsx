import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../features/auth/AuthPages', () => ({
  ForgotPasswordPage: () => <div>Forgot Password Page</div>,
  LoginPage: () => <div>Login Page</div>,
  RegisterPage: () => <div>Register Page</div>,
  ResetPasswordPage: () => <div>Reset Password Page</div>,
  VerifyEmailPage: () => <div>Verify Email Page</div>,
}))

vi.mock('../features/profile/ProfilePage', () => ({
  ProfilePage: () => <div>Profile Page</div>,
}))

vi.mock('../features/admin/AdminPages', () => ({
  AdminApplicationsPage: () => <div>Applications Page</div>,
  AdminUsersPage: () => <div>Users Page</div>,
}))

vi.mock('../features/catalog/CatalogPages', () => ({
  CatalogPage: () => <div>Catalog Page</div>,
  SearchPage: () => <div>Search Page</div>,
}))

vi.mock('../features/courses/CoursePages', () => ({
  CourseEditorPage: () => <div>Course Editor Page</div>,
  CourseWorkspacePage: () => <div>Course Workspace Page</div>,
}))

import { AppRoutes } from './router'
import { clearSession, setSession } from '../lib/session'

function renderRoutes(route: string) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <AppRoutes />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AppRoutes', () => {
  beforeEach(() => {
    clearSession()
  })

  afterEach(() => {
    clearSession()
    cleanup()
  })

  it('redirects signed-out users to login', () => {
    renderRoutes('/app/profile')

    expect(screen.getByText('Login Page')).toBeInTheDocument()
  })

  it('redirects non-admin users away from admin routes', () => {
    setSession({
      accessToken: 'token',
      refreshToken: 'refresh',
      tokenType: 'bearer',
      expiresIn: 900,
      user: {
        id: 'student-id',
        email: 'student@example.com',
        roles: ['student'],
      },
    })

    renderRoutes('/app/admin/users')

    expect(screen.getByText('Profile Page')).toBeInTheDocument()
  })

  it('sends signed-in students to the catalog by default', () => {
    setSession({
      accessToken: 'token',
      refreshToken: 'refresh',
      tokenType: 'bearer',
      expiresIn: 900,
      user: {
        id: 'student-id',
        email: 'student@example.com',
        roles: ['student'],
      },
    })

    renderRoutes('/login')

    expect(screen.getByText('Catalog Page')).toBeInTheDocument()
  })

  it('keeps admins on admin routes', () => {
    setSession({
      accessToken: 'token',
      refreshToken: 'refresh',
      tokenType: 'bearer',
      expiresIn: 900,
      user: {
        id: 'admin-id',
        email: 'admin@example.com',
        roles: ['admin'],
      },
    })

    renderRoutes('/app/admin/users')

    expect(screen.getByText('Users Page')).toBeInTheDocument()
  })

  it('keeps instructors on the course workspace', () => {
    setSession({
      accessToken: 'token',
      refreshToken: 'refresh',
      tokenType: 'bearer',
      expiresIn: 900,
      user: {
        id: 'instructor-id',
        email: 'instructor@example.com',
        roles: ['instructor'],
      },
    })

    renderRoutes('/app/courses')

    expect(screen.getByText('Course Workspace Page')).toBeInTheDocument()
  })

  it('redirects students from /app base to catalog', () => {
    setSession({
      accessToken: 'token',
      refreshToken: 'refresh',
      tokenType: 'bearer',
      expiresIn: 900,
      user: {
        id: 'student-id',
        email: 'student@example.com',
        roles: ['student'],
      },
    })

    renderRoutes('/app')

    expect(screen.getByText('Catalog Page')).toBeInTheDocument()
  })

  it('redirects instructors from /app base to courses', () => {
    setSession({
      accessToken: 'token',
      refreshToken: 'refresh',
      tokenType: 'bearer',
      expiresIn: 900,
      user: {
        id: 'instructor-id',
        email: 'instructor@example.com',
        roles: ['instructor'],
      },
    })

    renderRoutes('/app')

    expect(screen.getByText('Course Workspace Page')).toBeInTheDocument()
  })
})