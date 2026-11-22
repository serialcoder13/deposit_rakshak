import type { ReactNode } from 'react'
import clsx from 'clsx'

interface ProgressRingProps {
  value: number          // 0–100
  size?: number          // px, default 120
  stroke?: number        // px, default 10
  color?: string         // tailwind colour token or hex
  children?: ReactNode
  className?: string
}

export function ProgressRing({
  value,
  size = 120,
  stroke = 10,
  color = '#4F46E5',
  children,
  className,
}: ProgressRingProps) {
  const r = (size - stroke) / 2
  const circ = 2 * Math.PI * r
  const dash = circ * Math.min(Math.max(value, 0), 100) / 100

  return (
    <div
      className={clsx('relative inline-flex items-center justify-center', className)}
      style={{ width: size, height: size }}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ transform: 'rotate(-90deg)' }}
      >
        {/* track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={stroke}
        />
        {/* progress */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circ}`}
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
      </svg>
      {children && (
        <div className="absolute inset-0 flex items-center justify-center">
          {children}
        </div>
      )}
    </div>
  )
}
