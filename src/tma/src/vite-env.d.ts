/// <reference types="vite/client" />

interface Window {
  Telegram?: {
    WebApp?: {
      initData: string
      initDataUnsafe?: Record<string, unknown>
      themeParams?: Record<string, string>
      colorScheme?: string
      ready?: () => void
      expand?: () => void
      close?: () => void
      MainButton?: {
        text: string
        color: string
        textColor: string
        isVisible: boolean
        isActive: boolean
        show: () => void
        hide: () => void
        enable: () => void
        disable: () => void
        onClick: (callback: () => void) => void
        offClick: (callback: () => void) => void
      }
      BackButton?: {
        show: () => void
        hide: () => void
        onClick: (callback: () => void) => void
        offClick: (callback: () => void) => void
      }
    }
  }
}
