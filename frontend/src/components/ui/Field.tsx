import clsx from 'clsx'
import { forwardRef, type InputHTMLAttributes, type ReactNode, type TextareaHTMLAttributes } from 'react'

const fieldBox =
  'flex items-center bg-white border border-slate-200 rounded-2xl overflow-hidden transition-shadow ' +
  'focus-within:border-indigo-400 focus-within:ring-4 focus-within:ring-indigo-100'

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  hint?: ReactNode
  prefix?: ReactNode
  suffix?: ReactNode
}

export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, hint, prefix, suffix, className, ...props },
  ref,
) {
  return (
    <label className={clsx('block', className)}>
      {label && <span className="block text-sm font-semibold text-slate-700 mb-1.5">{label}</span>}
      <div className={fieldBox}>
        {prefix && (
          <span className="pl-4 pr-1 text-base font-semibold text-slate-500 select-none tabular-nums">{prefix}</span>
        )}
        <input
          ref={ref}
          className="flex-1 min-w-0 h-14 px-4 text-base text-slate-900 placeholder:text-slate-400 outline-none bg-transparent tabular-nums"
          {...props}
        />
        {suffix && <span className="pr-4 text-sm text-slate-500 select-none">{suffix}</span>}
      </div>
      {hint && <span className="block text-xs text-slate-500 mt-1.5">{hint}</span>}
    </label>
  )
})

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
}

export function TextArea({ label, className, ...props }: TextAreaProps) {
  return (
    <label className={clsx('block', className)}>
      {label && <span className="block text-sm font-semibold text-slate-700 mb-1.5">{label}</span>}
      <div className={fieldBox}>
        <textarea
          rows={3}
          className="flex-1 min-w-0 px-4 py-3.5 text-base text-slate-900 placeholder:text-slate-400 outline-none bg-transparent resize-none"
          {...props}
        />
      </div>
    </label>
  )
}

/** Horizontal set of selectable chips (single choice). */
export function ChoiceChips<T extends string>({
  options,
  value,
  onChange,
  className,
}: {
  options: { value: T; label: string; icon?: ReactNode }[]
  value: T | null
  onChange: (v: T) => void
  className?: string
}) {
  return (
    <div className={clsx('flex flex-wrap gap-2', className)}>
      {options.map((o) => {
        const on = o.value === value
        return (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            className={clsx(
              'h-11 px-4 rounded-full text-sm font-semibold inline-flex items-center gap-1.5 transition-all border',
              on
                ? 'bg-slate-900 text-white border-slate-900 shadow-soft'
                : 'bg-white text-slate-700 border-slate-200 hover:border-slate-300',
            )}
          >
            {o.icon}
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

/** Segmented tabs */
export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
}: {
  tabs: { value: T; label: string; count?: number }[]
  value: T
  onChange: (v: T) => void
}) {
  return (
    <div className="flex gap-1 p-1 bg-slate-100 rounded-2xl overflow-x-auto no-scrollbar">
      {tabs.map((t) => (
        <button
          key={t.value}
          type="button"
          onClick={() => onChange(t.value)}
          className={clsx(
            'flex-1 h-10 px-3 rounded-xl text-sm font-semibold whitespace-nowrap transition-all inline-flex items-center justify-center gap-1.5',
            value === t.value ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500',
          )}
        >
          {t.label}
          {t.count !== undefined && (
            <span
              className={clsx(
                'min-w-5 h-5 px-1.5 rounded-full text-[11px] leading-5 tabular-nums',
                value === t.value ? 'bg-slate-900 text-white' : 'bg-slate-200 text-slate-600',
              )}
            >
              {t.count}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}
