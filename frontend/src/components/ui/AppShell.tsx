import { motion, AnimatePresence } from 'framer-motion'
import { ArrowLeft, LogOut, Phone } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import clsx from 'clsx'
import { clearToken, type Role } from '../../api'
import { useMe } from '../../lib/hooks'
import { prettyPhone } from '../../lib/format'
import { Avatar, RoleBadge } from './Badge'

interface AppShellProps {
  title?: ReactNode
  /** true = go back in history, string = go to that path */
  back?: boolean | string
  role?: Role
  children: ReactNode
  /** Full-bleed area under the top bar (gradient heroes) */
  hero?: ReactNode
  /** Sticky bottom action bar */
  footer?: ReactNode
  /** Floating element rendered outside the scrolling column */
  floating?: ReactNode
  /** Transparent top bar on a gradient hero */
  dark?: boolean
}

export function AppShell({ title, back, role, children, hero, footer, floating, dark }: AppShellProps) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data: me } = useMe()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    const close = (e: PointerEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('pointerdown', close)
    return () => document.removeEventListener('pointerdown', close)
  }, [menuOpen])

  function handleBack() {
    if (typeof back === 'string') navigate(back)
    else if (window.history.length > 1) navigate(-1)
    else navigate('/')
  }

  function handleLogout() {
    clearToken()
    qc.clear()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-dvh flex flex-col">
      <header
        className={clsx(
          'sticky top-0 z-30 pt-safe',
          dark
            ? 'bg-indigo-700/70 backdrop-blur-xl text-white'
            : 'bg-white/80 backdrop-blur-xl border-b border-slate-200/60',
        )}
      >
        <div className="max-w-md mx-auto px-2 h-14 flex items-center gap-1">
          {back ? (
            <button
              onClick={handleBack}
              className={clsx(
                'h-12 w-12 flex items-center justify-center rounded-full transition-colors',
                dark ? 'hover:bg-white/10' : 'hover:bg-slate-100',
              )}
              aria-label="Go back"
            >
              <ArrowLeft className={clsx('w-5 h-5', dark ? 'text-white' : 'text-slate-700')} />
            </button>
          ) : (
            <div className="flex items-center gap-2 pl-2 pr-1">
              <img src="/logo.svg" alt="" className="w-8 h-8" />
            </div>
          )}
          <h1
            className={clsx(
              'flex-1 min-w-0 text-[17px] font-bold font-display truncate',
              dark ? 'text-white' : 'text-slate-900',
            )}
          >
            {title}
          </h1>
          {role && <RoleBadge role={role} dark={dark} />}
          {me && (
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen((o) => !o)}
                className="h-12 w-12 flex items-center justify-center rounded-full"
                aria-label="Account menu"
              >
                <Avatar name={me.name || me.phone} size="sm" />
              </button>
              <AnimatePresence>
                {menuOpen && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95, y: -4 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: -4 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-1 mt-1 w-60 origin-top-right bg-white rounded-2xl shadow-soft-lg border border-slate-100 overflow-hidden text-slate-900"
                  >
                    <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-3">
                      <Avatar name={me.name || me.phone} size="md" />
                      <div className="min-w-0">
                        <p className="text-sm font-semibold truncate">{me.name || 'Your account'}</p>
                        <p className="text-xs text-slate-500 flex items-center gap-1 tabular-nums">
                          <Phone className="w-3 h-3" />
                          {prettyPhone(me.phone)}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="w-full h-12 flex items-center gap-2 px-4 text-sm font-medium text-rose-600 hover:bg-rose-50 transition-colors"
                    >
                      <LogOut className="w-4 h-4" />
                      Log out
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>
      </header>

      {hero}

      <motion.main
        className={clsx('flex-1 max-w-md mx-auto w-full px-4 pt-4', footer ? 'pb-32' : 'pb-safe-8')}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.28, ease: 'easeOut' }}
      >
        {children}
      </motion.main>

      {footer && (
        <div className="fixed bottom-0 inset-x-0 z-30 bg-gradient-to-t from-page via-page/95 to-page/0 pt-6">
          <div className="max-w-md mx-auto px-4 pb-safe-4">{footer}</div>
        </div>
      )}
      {floating}
    </div>
  )
}
