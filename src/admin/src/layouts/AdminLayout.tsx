import { Layout, Menu, Typography } from 'antd'
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
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const { Header, Sider, Content } = Layout
const { Text } = Typography

export default function AdminLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()

  const menuItems = [
    { key: '/admin', icon: <DashboardOutlined />, label: 'Дашборд' },
    { key: '/admin/users', icon: <UserOutlined />, label: 'Пользователи' },
    { key: '/admin/scrolls', icon: <BookOutlined />, label: 'Свитки' },
    { key: '/admin/payments', icon: <DollarOutlined />, label: 'Платежи' },
    ...(user?.role === 'master' || user?.role === 'leader'
      ? [
          { key: '/admin/finance', icon: <FundOutlined />, label: 'Финансы' },
          { key: '/admin/moderation', icon: <SafetyOutlined />, label: 'Модерация' },
          { key: '/admin/broadcast', icon: <NotificationOutlined />, label: 'Рассылка' },
        ]
      : []),
    ...(user?.role === 'master'
      ? [{ key: '/admin/settings', icon: <SettingOutlined />, label: 'Настройки' }]
      : []),
    ...(user?.role === 'master' || user?.role === 'leader'
      ? [{ key: '/admin/audit', icon: <AuditOutlined />, label: 'Аудит' }]
      : []),
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible>
        <div style={{ height: 32, margin: 16, color: '#fff', fontWeight: 'bold', fontSize: 14, textAlign: 'center' }}>
          Игрок.Реальность
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 16 }}>
          <Text>{user?.username}</Text>
          <a onClick={logout} style={{ cursor: 'pointer' }}>Выйти</a>
        </Header>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
