import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import clsx from 'clsx'
import type { ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: ReactNode
  children: ReactNode
}

const base =
  'inline-flex items-center justify-center gap-2 font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50'

const variants: Record<Variant, string> = {
  primary:
    'bg-gradient-to-r from-indigo-600 via-violet-600 to-fuchsia-500 text-white shadow-soft focus-visible:ring-indigo-500',
  secondary:
    'bg-white text-slate-700 border border-slate-200 shadow-soft hover:bg-slate-50 focus-visible:ring-slate-400',
  ghost:
    'bg-transparent text-slate-600 hover:bg-slate-100 focus-visible:ring-slate-400',
  danger:
    'bg-danger text-white shadow-soft hover:bg-rose-700 focus-visible:ring-rose-500',
}

const sizes: Record<Size, string> = {
  md: 'h-11 px-5 text-sm rounded-2xl',
  lg: 'h-14 w-full px-6 text-base rounded-2xl',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  children,
  className,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <motion.div
      whileTap={{ scale: disabled || loading ? 1 : 0.97 }}
      transition={{ type: 'spring', stiffness: 400, damping: 20 }}
      className="inline-flex w-full"
      style={{ display: sizes[size].includes('w-full') ? 'flex' : 'inline-flex' }}
    >
      <button
        className={clsx(base, variants[variant], sizes[size], 'w-full', className)}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          icon && <span className="shrink-0">{icon}</span>
        )}
        {children}
      </button>
    </motion.div>
  )
}
