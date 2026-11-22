import { CheckCircle2 } from 'lucide-react'
import clsx from 'clsx'
import type { ReactNode } from 'react'

type StepState = 'done' | 'current' | 'upcoming'

export interface StepItem {
  title: string
  subtitle?: string
  state: StepState
  content?: ReactNode  // shown when state === 'current'
}

interface StepperProps {
  steps: StepItem[]
  className?: string
}

export function Stepper({ steps, className }: StepperProps) {
  return (
    <ol className={clsx('relative', className)}>
      {steps.map((step, i) => {
        const isLast = i === steps.length - 1
        return (
          <li key={i} className="flex gap-4">
            {/* connector column */}
            <div className="flex flex-col items-center">
              <StepDot state={step.state} />
              {!isLast && (
                <div
                  className={clsx(
                    'w-0.5 flex-1 my-1',
                    step.state === 'done' ? 'bg-emerald-400' : 'bg-slate-200',
                  )}
                />
              )}
            </div>
            {/* content column */}
            <div className={clsx('pb-5 flex-1', isLast && 'pb-0')}>
              <p
                className={clsx(
                  'text-sm font-semibold leading-5',
                  step.state === 'upcoming' ? 'text-slate-400' : 'text-slate-800',
                )}
              >
                {step.title}
              </p>
              {step.subtitle && (
                <p className="text-xs text-slate-500 mt-0.5">{step.subtitle}</p>
              )}
              {step.state === 'current' && step.content && (
                <div className="mt-3">{step.content}</div>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}

function StepDot({ state }: { state: StepState }) {
  if (state === 'done') {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500 shrink-0">
        <CheckCircle2 className="h-4 w-4 text-white" />
      </span>
    )
  }
  if (state === 'current') {
    return (
      <span className="relative flex h-6 w-6 shrink-0 items-center justify-center">
        <span className="absolute h-6 w-6 rounded-full bg-indigo-200 animate-ping opacity-60" />
        <span className="relative h-4 w-4 rounded-full bg-gradient-to-br from-indigo-600 to-fuchsia-500" />
      </span>
    )
  }
  return (
    <span className="h-6 w-6 rounded-full border-2 border-slate-200 bg-white shrink-0" />
  )
}
