import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Spin } from 'antd'
import { TmaAuthProvider, useTmaAuth } from './contexts/TmaAuthContext'
import TmaLayout from './layouts/TmaLayout'
import Dashboard from './pages/Dashboard'
import Users from './pages/Users'
import UserDetail from './pages/UserDetail'
import Scrolls from './pages/Scrolls'
import Payments from './pages/Payments'
import Finance from './pages/Finance'
import Moderation from './pages/Moderation'
import Settings from './pages/Settings'
import AuditLog from './pages/AuditLog'
import Broadcast from './pages/Broadcast'

function AuthGate({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading, error } = useTmaAuth()

  if (loading) {
    return (
      <div className="tma-loading">
        <Spin size="large" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="tma-error">
        <div className="tma-error__message">{error}</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="tma-error">
        <div className="tma-error__message">
          Авторизация не удалась. Попробуйте перезапустить приложение.
        </div>
      </div>
    )
  }

  return <>{children}</>
}

export default function App() {
  return (
    <TmaAuthProvider>
      <AuthGate>
        <BrowserRouter basename="/app">
          <Routes>
            <Route element={<TmaLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="users" element={<Users />} />
              <Route path="users/:id" element={<UserDetail />} />
              <Route path="scrolls" element={<Scrolls />} />
              <Route path="payments" element={<Payments />} />
              <Route path="finance" element={<Finance />} />
              <Route path="moderation" element={<Moderation />} />
              <Route path="settings" element={<Settings />} />
              <Route path="audit" element={<AuditLog />} />
              <Route path="broadcast" element={<Broadcast />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthGate>
    </TmaAuthProvider>
  )
}
