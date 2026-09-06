import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import api from '../services/api'

interface TmaAuthContextType {
  isAuthenticated: boolean
  user: { username: string; role: string } | null
  loading: boolean
  error: string | null
}

const TmaAuthContext = createContext<TmaAuthContextType | undefined>(undefined)

export function TmaAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<{ username: string; role: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const authenticate = useCallback(async () => {
    try {
      const tg = window.Telegram?.WebApp
      if (!tg) {
        setError('Telegram WebApp недоступен. Откройте приложение через Telegram.')
        setLoading(false)
        return
      }

      // Apply Telegram theme params to CSS variables
      if (tg.themeParams) {
        const root = document.documentElement
        const tp = tg.themeParams as Record<string, string>
        for (const [key, value] of Object.entries(tp)) {
          root.style.setProperty(`--tg-theme-${key}`, value)
        }
      }

      // Expand the Mini App to full height
      tg.expand?.()

      // Signal that Mini App is ready
      tg.ready?.()

      // Get initData
      const initData = tg.initData
      if (!initData) {
        setError('Не удалось получить данные Telegram. Откройте приложение через Telegram.')
        setLoading(false)
        return
      }

      // POST initData to /api/tma/auth to get JWT
      const response = await api.post('/tma/auth', { init_data: initData })
      const { access_token, user: userData } = response.data

      localStorage.setItem('tma_access_token', access_token)
      setUser(userData)
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Ошибка авторизации'
      setError(`Не удалось войти: ${message}`)
      localStorage.removeItem('tma_access_token')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    authenticate()
  }, [authenticate])

  return (
    <TmaAuthContext.Provider
      value={{ isAuthenticated: !!user, user, loading, error }}
    >
      {children}
    </TmaAuthContext.Provider>
  )
}

export function useTmaAuth(): TmaAuthContextType {
  const context = useContext(TmaAuthContext)
  if (!context) {
    throw new Error('useTmaAuth must be used within a TmaAuthProvider')
  }
  return context
}
