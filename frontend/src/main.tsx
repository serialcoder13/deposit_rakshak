import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import App from './App'
import { ApiError } from './api'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (count, err) => !(err instanceof ApiError && err.status < 500) && count < 2,
      staleTime: 2_000,
      refetchOnWindowFocus: true,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster
        richColors
        position="top-center"
        offset="calc(env(safe-area-inset-top) + 12px)"
        toastOptions={{ style: { borderRadius: 16, fontFamily: 'Inter, system-ui, sans-serif' } }}
      />
    </QueryClientProvider>
  </React.StrictMode>,
)
