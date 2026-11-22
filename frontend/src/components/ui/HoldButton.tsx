import { useEffect, useRef, useState, type ReactNode } from 'react'
import clsx from 'clsx'
import { Fingerprint, Loader2 } from 'lucide-react'

interface HoldButtonProps {
  label: string
  holdingLabel?: string
  onComplete: () => void
  disabled?: boolean
  loading?: boolean
  duration?: number
  icon?: ReactNode
}

/** Press and hold to confirm. Fills left to right over `duration` ms. */
export function HoldButton({
  label,
  holdingLabel = 'Keep holding…',
  onComplete,
  disabled,
  loading,
  duration = 1200,
  icon,
}: HoldButtonProps) {
  const [progress, setProgress] = useState(0)
  const [holding, setHolding] = useState(false)
  const raf = useRef(0)
  const t0 = useRef(0)
  const done = useRef(false)

  useEffect(() => () => cancelAnimationFrame(raf.current), [])

  function start() {
    if (disabled || loading) return
    done.current = false
    setHolding(true)
    t0.current = performance.now()
    navigator.vibrate?.(10)
    const tick = (now: number) => {
      const p = Math.min((now - t0.current) / duration, 1)
      setProgress(p)
      if (p >= 1) {
        done.current = true
        setHolding(false)
        navigator.vibrate?.([20, 40, 20])
        onComplete()
        setTimeout(() => setProgress(0), 400)
        return
      }
      raf.current = requestAnimationFrame(tick)
    }
    raf.current = requestAnimationFrame(tick)
  }

  function stop() {
    cancelAnimationFrame(raf.current)
    setHolding(false)
    if (!done.current) setProgress(0)
  }

  return (
    <button
      type="button"
      disabled={disabled || loading}
      onPointerDown={start}
      onPointerUp={stop}
      onPointerLeave={stop}
      onPointerCancel={stop}
      onContextMenu={(e) => e.preventDefault()}
      className={clsx(
        'relative w-full h-14 rounded-2xl overflow-hidden select-none touch-none font-semibold text-base',
        'bg-slate-900 text-white shadow-soft-lg disabled:opacity-50 disabled:cursor-not-allowed',
        holding && 'scale-[0.98]',
        'transition-transform',
      )}
      style={{ WebkitUserSelect: 'none', WebkitTouchCallout: 'none' } as React.CSSProperties}
    >
      <span
        className="absolute inset-y-0 left-0 bg-gradient-to-r from-indigo-600 via-violet-600 to-fuchsia-500"
        style={{ width: `${progress * 100}%` }}
      />
      <span className="relative z-10 flex items-center justify-center gap-2">
        {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : (icon ?? <Fingerprint className="w-5 h-5" />)}
        {holding ? holdingLabel : label}
      </span>
    </button>
  )
}
