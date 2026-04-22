import { NavLink } from 'react-router-dom'
import type { ReactNode } from 'react'

interface SidebarLink {
  to: string
  label: string
  icon?: ReactNode
}

interface SidebarSection {
  label?: string
  links: SidebarLink[]
}

interface SidebarProps {
  brand?: ReactNode
  sections: SidebarSection[]
}

export function Sidebar({ brand, sections }: SidebarProps) {
  return (
    <nav className="sidebar" aria-label="Sidebar navigation">
      {brand ? <div className="sidebar__brand">{brand}</div> : null}

      {sections.map((section, si) => (
        <div key={si} className="sidebar__section">
          {section.label ? <div className="sidebar__label">{section.label}</div> : null}
          {section.links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `sidebar__link${isActive ? ' active' : ''}`
              }
              end={
                link.to === '/app/dashboard'
                || link.to === '/app/courses'
                || link.to === '/app/admin'
              }
            >
              {link.icon ? <span className="sidebar__icon">{link.icon}</span> : null}
              {link.label}
            </NavLink>
          ))}
          {si < sections.length - 1 ? <div className="sidebar__divider" /> : null}
        </div>
      ))}
    </nav>
  )
}
