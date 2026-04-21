import { NavLink } from 'react-router-dom'

interface TabItem {
  to: string
  label: string
}

interface TabNavProps {
  items: TabItem[]
}

export function TabNav({ items }: TabNavProps) {
  return (
    <nav className="tab-nav">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end
          className={({ isActive }) =>
            `tab-nav__item${isActive ? ' active' : ''}`
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  )
}
