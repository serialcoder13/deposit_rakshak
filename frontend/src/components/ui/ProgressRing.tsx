import { useEffect, useId, useState, type ReactNode } from 'react'
import clsx from 'clsx'

interface ProgressRingProps {
  value: number // 0 to 100
  size?: number
  stroke?: number
  /** Solid colour; when omitted the brand gradient is used */
  color?: string
  track?: string
  children?: ReactNode
  className?: string
}

/** Animated SVG ring. Fills from 0 on mount. */
export function ProgressRing({ value, size = 120, stroke = 10, color, track = '#e2e8f0', children, className }: ProgressRingProps) {
  const id = useId().replace(/:/g, '')
  const [shown, setShown] = useState(0)
  useEffect(() => {
    const t = requestAnimationFrame(() => setShown(Math.min(Math.max(value, 0), 100)))
    return () => cancelAnimationFrame(t)
  }, [value])

  const r = (size - stroke) / 2
  const circ = 2 * Math.PI * r
  const dash = (circ * shown) / 100

  return (
    <div className={clsx('relative inline-flex items-center justify-center', className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
        <defs>
          <linearGradient id={`ring-${id}`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#4F46E5" />
            <stop offset="55%" stopColor="#7C3AED" />
            <stop offset="100%" stopColor="#D946EF" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color ?? `url(#ring-${id})`}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          style={{ transition: 'stroke-dasharray 1.2s cubic-bezier(.22,1,.36,1)' }}
        />
      </svg>
      {children && <div className="absolute inset-0 flex items-center justify-center">{children}</div>}
    </div>
  )
}
