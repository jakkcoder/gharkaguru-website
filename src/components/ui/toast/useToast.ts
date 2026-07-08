import { createContext, useContext } from 'react'

export type ToastVariant = 'success' | 'error' | 'warning' | 'info'

export type ToastItem = {
  id: string
  title: string
  description?: string
  variant: ToastVariant
}

export type ToastApi = {
  show: (t: Omit<ToastItem, 'id'>) => void
  success: (title: string, description?: string) => void
  error: (title: string, description?: string) => void
  warning: (title: string, description?: string) => void
  info: (title: string, description?: string) => void
}

export const ToastContext = createContext<ToastApi | null>(null)

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within <ToastProvider>')
  return ctx
}

