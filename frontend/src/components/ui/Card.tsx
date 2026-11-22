import clsx from 'clsx'
import type { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  onClick?: () => void
}

export function Card({ children, className, onClick }: CardProps) {
  return (
    <div
      className={clsx(
        'bg-white rounded-3xl shadow-soft p-5',
        onClick && 'cursor-pointer active:scale-[0.99] transition-transform',
        className,
      )}
      onClick={onClick}
    >
      {children}
    </div>
  )
}

export function GlassCard({ children, className }: CardProps) {
  return (
    <div
      className={clsx(
        'bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-5',
        className,
      )}
    >
      {children}
    </div>
  )
}
