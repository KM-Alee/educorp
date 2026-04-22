import { Link, Outlet } from 'react-router-dom'
import { useMemo } from 'react'
import type { ReactNode } from 'react'
import {
  LayoutDashboard,
  BookOpen,
  Award,
  PenLine,
  Compass,
  Search,
  Users,
  ClipboardList,
  BarChart3,
  Zap,
  ScrollText,
  Wrench,
  Bell,
  User,
  Settings,
  BookOpenCheck,
} from 'lucide-react'

import { Sidebar } from '../../components/navigation/Sidebar'
import { TopBar } from '../../components/navigation/TopBar'
import { useSessionState } from '../../lib/session'

const ICON_SIZE = 18

function buildSidebarSections(roles: string[]) {
  const isStudent = roles.includes('student')
  const isInstructor = roles.includes('instructor') || roles.includes('admin')
  const isAdmin = roles.includes('admin')

  const sections: Array<{ label?: string; links: Array<{ to: string; label: string; icon?: ReactNode }> }> = []

  // Student section
  if (isStudent) {
    sections.push({
      links: [
        { to: '/app/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={ICON_SIZE} /> },
        { to: '/app/learning', label: 'My Learning', icon: <BookOpen size={ICON_SIZE} /> },
        { to: '/app/certificates', label: 'Certificates', icon: <Award size={ICON_SIZE} /> },
      ],
    })
  }

  // Instructor section
  if (isInstructor) {
    sections.push({
      links: [
        { to: '/app/courses', label: 'My Courses', icon: <PenLine size={ICON_SIZE} /> },
      ],
    })
  }

  // Shared section
  sections.push({
    links: [
      { to: '/app/catalog', label: 'Catalog', icon: <Compass size={ICON_SIZE} /> },
      { to: '/app/search', label: 'Search', icon: <Search size={ICON_SIZE} /> },
    ],
  })

  // Admin section
  if (isAdmin) {
    sections.push({
      label: 'Admin',
      links: [
        { to: '/app/admin', label: 'Dashboard', icon: <LayoutDashboard size={ICON_SIZE} /> },
        { to: '/app/admin/users', label: 'Users', icon: <Users size={ICON_SIZE} /> },
        { to: '/app/admin/instructor-applications', label: 'Applications', icon: <ClipboardList size={ICON_SIZE} /> },
        { to: '/app/admin/enrollments', label: 'Enrollments', icon: <BookOpenCheck size={ICON_SIZE} /> },
        { to: '/app/admin/analytics', label: 'Analytics', icon: <BarChart3 size={ICON_SIZE} /> },
        { to: '/app/admin/workflows', label: 'Publishing Queue', icon: <Zap size={ICON_SIZE} /> },
        { to: '/app/admin/audit-log', label: 'Activity Log', icon: <ScrollText size={ICON_SIZE} /> },
        { to: '/app/admin/dlq', label: 'Failed Messages', icon: <Wrench size={ICON_SIZE} /> },
      ],
    })
  }

  // Bottom section
  sections.push({
    links: [
      { to: '/app/notifications', label: 'Notifications', icon: <Bell size={ICON_SIZE} /> },
      { to: '/app/profile', label: 'Profile', icon: <User size={ICON_SIZE} /> },
      { to: '/app/settings', label: 'Settings', icon: <Settings size={ICON_SIZE} /> },
    ],
  })

  return sections
}

export function AppShell() {
  const session = useSessionState()

  const sidebarSections = useMemo(
    () => buildSidebarSections(session?.user.roles ?? []),
    [session?.user.roles],
  )

  if (!session) return null

  return (
    <div className="app-shell">
      <div className="app-body">
        <Sidebar
          brand={<Link to="/app/dashboard">EduCorp</Link>}
          sections={sidebarSections}
        />
        <div className="app-content">
          <TopBar session={session} />
          <main className="app-main">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}
