import clsx from 'clsx'
import { AnimatePresence, motion } from 'framer-motion'
import { WifiOff } from 'lucide-react'
import { useOnline } from '../../lib/hooks'

/** Three dots for severity 0..3 */
export function SeverityDots({ value }: { value: number }) {
  const colors = ['bg-emerald-400', 'bg-amber-400', 'bg-orange-500', 'bg-rose-600']
  return (
    <span className="inline-flex items-center gap-1" aria-label={`Severity ${value} of 3`}>
      {[1, 2, 3].map((i) => (
        <span key={i} className={clsx('w-2 h-2 rounded-full', i <= value ? colors[value] : 'bg-slate-200')} />
      ))}
    </span>
  )
}

export function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(Math.min(Math.max(value, 0), 1) * 100)
  return (
    <span className="inline-flex items-center gap-2">
      <span className="w-16 h-1.5 rounded-full bg-slate-200 overflow-hidden">
        <motion.span
          className="block h-full rounded-full bg-gradient-to-r from-indigo-500 to-fuchsia-500"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </span>
      <span className="text-xs font-semibold text-slate-600 tabular-nums">{pct}%</span>
    </span>
  )
}

export function OfflineBanner() {
  const online = useOnline()
  return (
    <AnimatePresence>
      {!online && (
        <motion.div
          initial={{ y: -40, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -40, opacity: 0 }}
          className="fixed top-0 inset-x-0 z-[60] pt-safe bg-amber-500 text-white"
        >
          <div className="max-w-md mx-auto px-4 h-9 flex items-center justify-center gap-2 text-sm font-semibold">
            <WifiOff className="w-4 h-4" />
            You are offline. Changes will fail until you reconnect.
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

/** Small label + value pair */
export function Stat({ label, value, className }: { label: string; value: React.ReactNode; className?: string }) {
  return (
    <div className={className}>
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
      <p className="font-display font-bold text-slate-900 tabular-nums mt-0.5">{value}</p>
    </div>
  )
}

export function SectionTitle({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between mt-7 mb-3 px-1">
      <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">{children}</h2>
      {action}
    </div>
  )
}
