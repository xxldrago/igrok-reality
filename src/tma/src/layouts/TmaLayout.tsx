import { useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  DashboardOutlined,
  UserOutlined,
  BookOutlined,
  DollarOutlined,
  FundOutlined,
  SafetyOutlined,
  SettingOutlined,
  AuditOutlined,
} from '@ant-design/icons'
import { useTmaAuth } from '../contexts/TmaAuthContext'

const navItems = [
  { key: '/app', icon: <DashboardOutlined />, label: 'Дашборд' },
  { key: '/app/users', icon: <UserOutlined />, label: 'Юзеры' },
  { key: '/app/scrolls', icon: <BookOutlined />, label: 'Свитки' },
  { key: '/app/payments', icon: <DollarOutlined />, label: 'Платежи' },
]

const roleNavItems = [
  {
    key: '/app/finance',
    icon: <FundOutlined />,
    label: 'Финансы',
    roles: ['master', 'leader'],
  },
  {
    key: '/app/moderation',
    icon: <SafetyOutlined />,
    label: 'Модерация',
    roles: ['master', 'leader'],
  },
  {
    key: '/app/settings',
    icon: <SettingOutlined />,
    label: 'Настройки',
    roles: ['master'],
  },
  {
    key: '/app/audit',
    icon: <AuditOutlined />,
    label: 'Аудит',
    roles: ['master', 'leader'],
  },
]

export default function TmaLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useTmaAuth()

  // Handle Telegram BackButton
  useEffect(() => {
    const bb = window.Telegram?.WebApp?.BackButton
    if (bb) {
      bb?.show()
      const handler = () => {
        if (location.pathname === '/app/users') {
          // At root users page — close the mini app
          window.Telegram?.WebApp?.close?.()
        } else {
          navigate(-1)
        }
      }
      bb?.onClick(handler)
      return () => {
        bb?.offClick(handler)
        bb?.hide()
      }
    }
  }, [navigate, location.pathname])

  const visibleRoleItems = roleNavItems.filter((item) =>
    item.roles.includes(user?.role ?? ''),
  )

  const allNavItems = [...navItems, ...visibleRoleItems]

  return (
    <div className="tma-layout">
      <div className="tma-header">
        <div className="tma-header__title">Игрок.Реальность</div>
        {user?.role && (
          <div className="tma-header__badge">{user.role}</div>
        )}
      </div>
      <div className="tma-content">
        <Outlet />
      </div>
      <nav className="tma-bottom-nav">
        {allNavItems.map((item) => (
          <div
            key={item.key}
            className={`tma-bottom-nav__item ${
              location.pathname === item.key || location.pathname.startsWith(item.key + '/')
                ? 'tma-bottom-nav__item--active'
                : ''
            }`}
            onClick={() => navigate(item.key)}
          >
            <span className="tma-bottom-nav__icon">{item.icon}</span>
            <span>{item.label}</span>
          </div>
        ))}
      </nav>
    </div>
  )
}
