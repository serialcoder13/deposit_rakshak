import clsx from 'clsx'
import type { ReactNode } from 'react'
import { Button } from './Button'
import type { LucideIcon } from 'lucide-react'

// ── Skeleton ─────────────────────────────────────────────────────────────────

interface SkeletonProps {
  className?: string
  rounded?: string
}

export function Skeleton({ className, rounded = 'rounded-xl' }: SkeletonProps) {
  return (
    <div className={clsx('skeleton', rounded, className)} />
  )
}

export function SkeletonCard() {
  return (
    <div className="bg-white rounded-3xl shadow-soft p-5 space-y-3">
      <Skeleton className="h-5 w-2/3" />
      <Skeleton className="h-4 w-1/2" />
      <Skeleton className="h-10 w-full" />
    </div>
  )
}

// ── EmptyState ───────────────────────────────────────────────────────────────

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  text?: string
  action?: {
    label: string
    onClick: () => void
  }
  className?: string
}

export function EmptyState({ icon: Icon, title, text, action, className }: EmptyStateProps) {
  return (
    <div className={clsx('flex flex-col items-center justify-center py-16 px-6 text-center', className)}>
      <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
        <Icon className="w-8 h-8 text-slate-400" />
      </div>
      <p className="text-base font-semibold text-slate-700 mb-1">{title}</p>
      {text && <p className="text-sm text-slate-500 mb-4">{text}</p>}
      {action && (
        <Button variant="secondary" size="md" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  )
}
