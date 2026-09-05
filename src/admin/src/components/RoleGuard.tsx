import { type ReactNode } from 'react'
import { useAuth } from '../contexts/AuthContext'

interface RoleGuardProps {
  roles: string[]
  children: ReactNode
}

export default function RoleGuard({ roles, children }: RoleGuardProps) {
  const { user } = useAuth()

  if (!user || !roles.includes(user.role)) {
    return null
  }

  return <>{children}</>
}
