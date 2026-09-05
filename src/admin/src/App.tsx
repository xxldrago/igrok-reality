import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Spin } from 'antd'
import { useAuth } from './contexts/AuthContext'
import Login from './pages/Login'
import AdminLayout from './layouts/AdminLayout'
import Users from './pages/Users'
import Scrolls from './pages/Scrolls'
import Payments from './pages/Payments'
import Settings from './pages/Settings'
import AuditLog from './pages/AuditLog'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}><Spin size="large" /></div>
  }

  if (!isAuthenticated) {
    return <Navigate to="/admin/login" replace />
  }

  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/admin/login" element={<Login />} />
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<div>Добро пожаловать в админ-панель</div>} />
          <Route path="users" element={<Users />} />
          <Route path="scrolls" element={<Scrolls />} />
          <Route path="payments" element={<Payments />} />
          <Route path="settings" element={<Settings />} />
          <Route path="audit" element={<AuditLog />} />
        </Route>
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
