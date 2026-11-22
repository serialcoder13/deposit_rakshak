import { useEffect, useRef } from 'react'
import clsx from 'clsx'

interface OtpInputProps {
  value: string
  onChange: (v: string) => void
  onComplete?: (v: string) => void
  length?: number
  disabled?: boolean
  error?: boolean
}

/** Six boxes with auto-advance, backspace-to-previous and paste support. */
export function OtpInput({ value, onChange, onComplete, length = 6, disabled, error }: OtpInputProps) {
  const refs = useRef<(HTMLInputElement | null)[]>([])

  useEffect(() => {
    refs.current[0]?.focus()
  }, [])

  function setAt(index: number, digits: string) {
    const chars = value.padEnd(length, ' ').split('')
    let i = index
    for (const d of digits) {
      if (i >= length) break
      chars[i] = d
      i++
    }
    const next = chars.join('').replace(/\s+$/, '').replace(/\s/g, '')
    onChange(next)
    const focusAt = Math.min(i, length - 1)
    refs.current[focusAt]?.focus()
    if (next.length === length) onComplete?.(next)
  }

  return (
    <div className="flex justify-between gap-2">
      {Array.from({ length }).map((_, i) => (
        <input
          key={i}
          ref={(el) => {
            refs.current[i] = el
          }}
          value={value[i] ?? ''}
          disabled={disabled}
          inputMode="numeric"
          autoComplete={i === 0 ? 'one-time-code' : 'off'}
          aria-label={`Digit ${i + 1}`}
          maxLength={length}
          onFocus={(e) => e.target.select()}
          onChange={(e) => {
            const digits = e.target.value.replace(/\D/g, '')
            if (!digits) return
            // Typing into a filled box: keep the last typed digit; autofill/paste: spread
            setAt(i, digits.length > 1 && digits.length < length ? digits.slice(-1) : digits)
          }}
          onKeyDown={(e) => {
            if (e.key === 'Backspace') {
              e.preventDefault()
              if (value[i]) {
                onChange(value.slice(0, i) + value.slice(i + 1))
              } else if (i > 0) {
                onChange(value.slice(0, i - 1) + value.slice(i))
                refs.current[i - 1]?.focus()
              }
            } else if (e.key === 'ArrowLeft' && i > 0) refs.current[i - 1]?.focus()
            else if (e.key === 'ArrowRight' && i < length - 1) refs.current[i + 1]?.focus()
          }}
          onPaste={(e) => {
            e.preventDefault()
            const digits = e.clipboardData.getData('text').replace(/\D/g, '')
            if (digits) setAt(0, digits)
          }}
          className={clsx(
            'w-12 h-14 text-center text-2xl font-display font-bold tabular-nums rounded-2xl border bg-white outline-none transition-all',
            'focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100',
            error ? 'border-rose-400 animate-shake' : value[i] ? 'border-slate-300' : 'border-slate-200',
          )}
        />
      ))}
    </div>
  )
}
