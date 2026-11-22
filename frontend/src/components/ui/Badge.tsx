import clsx from 'clsx'
import { Home, KeyRound } from 'lucide-react'
import type { Role } from '../../api'

export function RoleBadge({ role, dark }: { role: Role; dark?: boolean }) {
  const Icon = role === 'owner' ? Home : KeyRound
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 h-7 px-2.5 rounded-full text-xs font-bold',
        dark
          ? 'bg-white/15 text-white border border-white/25'
          : role === 'owner'
            ? 'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-100'
            : 'bg-teal-50 text-teal-700 ring-1 ring-teal-100',
      )}
    >
      <Icon className="w-3.5 h-3.5" />
      {role === 'owner' ? 'Owner' : 'Tenant'}
    </span>
  )
}

const sizeClasses = {
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-12 h-12 text-base',
}

function initials(name: string) {
  const clean = name.trim()
  if (!clean) return '?'
  if (/^\+?\d[\d\s]*$/.test(clean)) return clean.replace(/\D/g, '').slice(-2)
  const parts = clean.split(/\s+/)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

export function Avatar({
  name,
  size = 'md',
  tone = 'brand',
  className,
}: {
  name: string
  size?: 'sm' | 'md' | 'lg'
  tone?: 'brand' | 'owner' | 'tenant'
  className?: string
}) {
  return (
    <div
      className={clsx(
        'rounded-full flex items-center justify-center font-display font-bold text-white shrink-0',
        tone === 'brand' && 'bg-gradient-to-br from-indigo-500 to-fuchsia-500',
        tone === 'owner' && 'bg-gradient-to-br from-indigo-500 to-indigo-700',
        tone === 'tenant' && 'bg-gradient-to-br from-teal-400 to-teal-700',
        sizeClasses[size],
        className,
      )}
    >
      {initials(name)}
    </div>
  )
}
