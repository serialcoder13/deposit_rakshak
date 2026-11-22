import clsx from 'clsx'
import type { ReactNode } from 'react'

// ── RoleBadge ─────────────────────────────────────────────────────────────────

type Role = 'owner' | 'tenant'

export function RoleBadge({ role }: { role: Role }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wide',
        role === 'owner' ? 'bg-indigo-100 text-indigo-700' : 'bg-teal-100 text-teal-700',
      )}
    >
      {role === 'owner' ? 'Owner' : 'Tenant'}
    </span>
  )
}

// ── Avatar ────────────────────────────────────────────────────────────────────

interface AvatarProps {
  name: string
  size?: 'sm' | 'md' | 'lg'
  className?: string
  children?: ReactNode
}

const sizeClasses = {
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-12 h-12 text-base',
}

function initials(name: string) {
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

export function Avatar({ name, size = 'md', className }: AvatarProps) {
  return (
    <div
      className={clsx(
        'rounded-full bg-gradient-to-br from-indigo-500 to-fuchsia-500',
        'flex items-center justify-center font-display font-bold text-white shrink-0',
        sizeClasses[size],
        className,
      )}
    >
      {initials(name)}
    </div>
  )
}
