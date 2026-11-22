import { motion, AnimatePresence } from 'framer-motion'
import { ArrowLeft, LogOut } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { clearToken } from '../../api'
import { Avatar } from './Badge'
import { RoleBadge } from './Badge'

interface AppShellProps {
  title?: string
  back?: boolean | string   // true = navigate(-1), string = navigate(to)
  role?: 'owner' | 'tenant'
  userName?: string
  children: ReactNode
  /** Renders a brand-gradient hero area above the page body */
  hero?: ReactNode
  className?: string
}

/** Page-level enter animation */
const pageVariants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit:    { opacity: 0, y: -6 },
}

export function AppShell({
  title,
  back,
  role,
  userName,
  children,
  hero,
  className,
}: AppShellProps) {
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  function handleBack() {
    if (typeof back === 'string') navigate(back)
    else navigate(-1)
  }

  function handleLogout() {
    clearToken()
    navigate('/login')
  }

  return (
    <div className={clsx('min-h-dvh flex flex-col', className)}>
      {/* ── Top bar ── */}
      <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-100 pt-safe">
        <div className="max-w-md mx-auto px-4 h-14 flex items-center gap-3">
          {back && (
            <button
              onClick={handleBack}
              className="p-2 -ml-2 rounded-full hover:bg-slate-100 transition-colors"
              aria-label="Go back"
            >
              <ArrowLeft className="w-5 h-5 text-slate-600" />
            </button>
          )}
          <h1 className="flex-1 text-base font-semibold font-display text-slate-800 truncate">
            {title}
          </h1>
          {role && <RoleBadge role={role} />}
          {userName && (
            <div className="relative">
              <button onClick={() => setMenuOpen(o => !o)} className="rounded-full">
                <Avatar name={userName} size="sm" />
              </button>
              <AnimatePresence>
                {menuOpen && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95, y: -4 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: -4 }}
                    transition={{ duration: 0.15 }}
                    className="absolute right-0 mt-2 w-44 bg-white rounded-2xl shadow-soft-lg border border-slate-100 overflow-hidden"
                  >
                    <div className="px-4 py-3 border-b border-slate-100">
                      <p className="text-xs text-slate-500">Signed in as</p>
                      <p className="text-sm font-semibold text-slate-800 truncate">{userName}</p>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2 px-4 py-3 text-sm text-danger hover:bg-rose-50 transition-colors"
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

      {/* ── Hero slot ── */}
      {hero}

      {/* ── Page body ── */}
      <motion.main
        className="flex-1 max-w-md mx-auto w-full px-4 pb-safe"
        variants={pageVariants}
        initial="initial"
        animate="animate"
        exit="exit"
        transition={{ duration: 0.25, ease: 'easeOut' }}
      >
        {children}
      </motion.main>
    </div>
  )
}
