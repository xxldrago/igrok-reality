import { Layout, Menu, Typography, Grid } from 'antd'
import { MenuOutlined } from '@ant-design/icons'
import {
  DashboardOutlined,
  UserOutlined,
  BookOutlined,
  DollarOutlined,
  FundOutlined,
  SafetyOutlined,
  SettingOutlined,
  AuditOutlined,
  NotificationOutlined,
  QuestionCircleOutlined,
  IdcardOutlined,
  TeamOutlined,
  TrophyOutlined,
  WalletOutlined,
} from '@ant-design/icons'
import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const { Header, Sider, Content } = Layout
const { Text } = Typography
const { useBreakpoint } = Grid

export default function AdminLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const screens = useBreakpoint()
  const isMobile = !screens.md
  const [collapsed, setCollapsed] = useState(false)

  const menuItems = [
    { key: '/admin', icon: <DashboardOutlined />, label: 'Дашборд' },
    { key: '/admin/users', icon: <UserOutlined />, label: 'Пользователи' },
    { key: '/admin/scrolls', icon: <BookOutlined />, label: 'Свитки' },
    { key: '/admin/payments', icon: <DollarOutlined />, label: 'Платежи' },
    ...(user?.role === 'master' || user?.role === 'leader'
      ? [
          { key: '/admin/finance', icon: <FundOutlined />, label: 'Финансы' },
          { key: '/admin/moderation', icon: <SafetyOutlined />, label: 'Модерация' },
          { key: '/admin/groups', icon: <TeamOutlined />, label: 'Группы' },
          { key: '/admin/specialist-quests', icon: <TrophyOutlined />, label: 'Квесты спец.' },
          { key: '/admin/broadcast', icon: <NotificationOutlined />, label: 'Рассылка' },
        ]
      : []),
    ...(user?.role === 'master'
      ? [
          { key: '/admin/commissions', icon: <WalletOutlined />, label: 'Комиссии' },
          { key: '/admin/settings', icon: <SettingOutlined />, label: 'Настройки' },
        ]
      : []),
    ...(user?.role === 'master' || user?.role === 'leader'
      ? [{ key: '/admin/quiz', icon: <QuestionCircleOutlined />, label: 'Входной тест' }]
      : []),
    ...(user?.role === 'master' || user?.role === 'leader'
      ? [{ key: '/admin/audit', icon: <AuditOutlined />, label: 'Аудит' }]
      : []),
    { key: '/admin/profile', icon: <IdcardOutlined />, label: 'Профиль' },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        theme="dark"
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        breakpoint="lg"
        collapsedWidth={isMobile ? 0 : 80}
        width={isMobile ? 240 : 200}
        trigger={null}
        style={{ position: isMobile ? 'fixed' : 'relative', height: '100vh', zIndex: 30, overflow: 'auto' }}
      >
        <div style={{ height: 32, margin: 16, color: '#fff', fontWeight: 'bold', fontSize: 14, textAlign: 'center', whiteSpace: 'nowrap' }}>
          {isMobile && collapsed ? 'Игрок' : 'Игрок.Реальность'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => {
            navigate(key)
            if (isMobile) setCollapsed(true)
          }}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 12px', display: 'flex', alignItems: 'center', gap: 12 }}>
          <MenuOutlined
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: 18, cursor: 'pointer' }}
          />
          <div style={{ flex: 1 }} />
          <Text>{user?.username}</Text>
          <a onClick={logout} style={{ cursor: 'pointer' }}>Выйти</a>
        </Header>
        <Content style={{ margin: isMobile ? 12 : 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}