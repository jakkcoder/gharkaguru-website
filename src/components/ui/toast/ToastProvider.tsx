import type { ReactNode } from 'react'
import { useCallback, useMemo, useState } from 'react'
import * as Toast from '@radix-ui/react-toast'
import { X } from 'lucide-react'
import { cn } from '../../../lib/cn'
import { ToastContext, type ToastApi, type ToastItem, type ToastVariant } from './useToast'

function variantStyles(variant: ToastVariant) {
  switch (variant) {
    case 'success':
      return 'border-tn-success/30'
    case 'error':
      return 'border-tn-error/30'
    case 'warning':
      return 'border-tn-warning/30'
    case 'info':
    default:
      return 'border-tn-border'
  }
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])

  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((x) => x.id !== id))
  }, [])

  const show = useCallback((t: Omit<ToastItem, 'id'>) => {
    const id = crypto.randomUUID()
    setItems((prev) => [{ id, ...t }, ...prev].slice(0, 5))
  }, [])

  const api = useMemo<ToastApi>(
    () => ({
      show,
      success: (title, description) => show({ title, description, variant: 'success' }),
      error: (title, description) => show({ title, description, variant: 'error' }),
      warning: (title, description) => show({ title, description, variant: 'warning' }),
      info: (title, description) => show({ title, description, variant: 'info' }),
    }),
    [show],
  )

  return (
    <ToastContext.Provider value={api}>
      <Toast.Provider swipeDirection="right" duration={4000}>
        {children}
        {items.map((t) => (
          <Toast.Root
            key={t.id}
            open
            onOpenChange={(open) => {
              if (!open) dismiss(t.id)
            }}
            className={cn(
              'grid w-[360px] gap-1 rounded-xl border bg-white p-4 shadow-soft',
              variantStyles(t.variant),
              'data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
              'data-[state=open]:slide-in-from-right-2 data-[state=closed]:slide-out-to-right-2',
            )}
          >
            <Toast.Title className="text-sm font-semibold text-tn-text">{t.title}</Toast.Title>
            {t.description ? (
              <Toast.Description className="text-sm text-tn-muted">{t.description}</Toast.Description>
            ) : null}
            <Toast.Close asChild>
              <button
                className="absolute right-2 top-2 rounded-md p-1.5 text-tn-muted hover:bg-tn-bg focus:outline-none focus-visible:ring-2 focus-visible:ring-tn-primary focus-visible:ring-offset-2"
                aria-label="Close notification"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </Toast.Close>
          </Toast.Root>
        ))}
        <Toast.Viewport className="fixed bottom-4 right-4 z-[60] flex max-h-screen w-[360px] flex-col gap-2 outline-none" />
      </Toast.Provider>
    </ToastContext.Provider>
  )
}

