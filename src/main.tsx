import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HelmetProvider } from 'react-helmet-async'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router-dom'
import './index.css'
import { router } from './router'
import { ToastProvider } from './components/ui/toast/ToastProvider'
import { AuthProvider } from './features/auth/AuthProvider'

async function enableMocking() {
  if (import.meta.env.PROD) return
  if (import.meta.env.MODE === 'test') return
  if (import.meta.env.VITE_DISABLE_MSW === 'true') return
  // If a real backend is configured, don't intercept with MSW.
  const base = (import.meta.env.VITE_API_BASE_URL ?? '').toString().trim()
  if (base) return
  const { worker } = await import('./mocks/browser')
  await worker.start({
    onUnhandledRequest: 'bypass',
  })
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

enableMocking().then(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <HelmetProvider>
        <ToastProvider>
          <AuthProvider>
            <QueryClientProvider client={queryClient}>
              <RouterProvider router={router} />
            </QueryClientProvider>
          </AuthProvider>
        </ToastProvider>
      </HelmetProvider>
    </StrictMode>,
  )
})
