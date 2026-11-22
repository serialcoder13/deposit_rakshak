import { useEffect, useRef, useState } from 'react'
import clsx from 'clsx'

interface MoneyProps {
  value: number
  className?: string
  /** If true, animate from 0 (or previous value) over 0.8s */
  countUp?: boolean
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const sizeClasses = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-2xl',
  xl: 'text-4xl',
}

function formatINR(n: number) {
  return '₹' + Math.round(n).toLocaleString('en-IN')
}

export function Money({ value, className, countUp = false, size = 'md' }: MoneyProps) {
  const [displayed, setDisplayed] = useState(countUp ? 0 : value)
  const prevRef = useRef(value)
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    if (!countUp) {
      setDisplayed(value)
      return
    }
    const start = prevRef.current
    const end = value
    prevRef.current = value
    if (start === end) return

    const duration = 800
    const startTime = performance.now()

    function step(now: number) {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplayed(start + (end - start) * eased)
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(step)
      }
    }
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = requestAnimationFrame(step)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [value, countUp])

  return (
    <span className={clsx('font-display tabular-nums font-semibold', sizeClasses[size], className)}>
      {formatINR(displayed)}
    </span>
  )
}
