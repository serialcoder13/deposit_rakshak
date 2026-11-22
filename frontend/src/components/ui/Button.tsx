import { motion, type HTMLMotionProps } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import clsx from 'clsx'
import type { ReactNode } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'tenant' | 'success' | 'glass'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends Omit<HTMLMotionProps<'button'>, 'children'> {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: ReactNode
  iconRight?: ReactNode
  block?: boolean
  children?: ReactNode
}

const base =
  'relative inline-flex items-center justify-center gap-2 font-semibold select-none transition-colors ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 ' +
  'disabled:cursor-not-allowed disabled:opacity-50'

const variants: Record<Variant, string> = {
  primary:
    'bg-gradient-to-r from-indigo-600 via-violet-600 to-fuchsia-500 text-white shadow-[0_10px_30px_-10px_rgba(124,58,237,.7)] focus-visible:ring-indigo-500',
  secondary: 'bg-white text-slate-800 border border-slate-200 shadow-sm hover:bg-slate-50 focus-visible:ring-slate-400',
  ghost: 'bg-transparent text-slate-600 hover:bg-slate-100 focus-visible:ring-slate-400',
  danger: 'bg-rose-600 text-white shadow-soft hover:bg-rose-700 focus-visible:ring-rose-500',
  tenant: 'bg-teal-600 text-white shadow-[0_10px_30px_-10px_rgba(13,148,136,.7)] hover:bg-teal-700 focus-visible:ring-teal-500',
  success: 'bg-emerald-500 text-white shadow-soft hover:bg-emerald-600 focus-visible:ring-emerald-500',
  glass: 'bg-white/15 text-white border border-white/25 backdrop-blur-xl hover:bg-white/25 focus-visible:ring-white',
}

const sizes: Record<Size, string> = {
  sm: 'h-10 px-4 text-sm rounded-xl',
  md: 'h-12 px-5 text-sm rounded-2xl',
  lg: 'h-14 px-6 text-base rounded-2xl',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  iconRight,
  block,
  children,
  className,
  disabled,
  type = 'button',
  ...props
}: ButtonProps) {
  const isBlock = block ?? size === 'lg'
  return (
    <motion.button
      type={type}
      whileTap={disabled || loading ? undefined : { scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 500, damping: 25 }}
      className={clsx(base, variants[variant], sizes[size], isBlock && 'w-full', className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : icon && <span className="shrink-0">{icon}</span>}
      {children}
      {!loading && iconRight && <span className="shrink-0">{iconRight}</span>}
    </motion.button>
  )
}
