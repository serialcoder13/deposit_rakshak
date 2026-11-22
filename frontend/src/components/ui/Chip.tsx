import clsx from 'clsx'
import type { ReactNode } from 'react'
import {
  AlertTriangle,
  Hourglass,
  History,
  ShieldCheck,
  Eye,
  CheckCircle2,
} from 'lucide-react'
import type { FindingClassification } from '../../api'

interface ChipProps {
  children: ReactNode
  tone?: 'rose' | 'slate' | 'sky' | 'violet' | 'amber' | 'emerald' | 'indigo' | 'teal'
  icon?: ReactNode
  className?: string
}

const toneClasses: Record<NonNullable<ChipProps['tone']>, string> = {
  rose:    'bg-rose-100 text-rose-700',
  slate:   'bg-slate-100 text-slate-600',
  sky:     'bg-sky-100 text-sky-700',
  violet:  'bg-violet-100 text-violet-700',
  amber:   'bg-amber-100 text-amber-700',
  emerald: 'bg-emerald-100 text-emerald-700',
  indigo:  'bg-indigo-100 text-indigo-700',
  teal:    'bg-teal-100 text-teal-700',
}

export function Chip({ children, tone = 'slate', icon, className }: ChipProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold',
        toneClasses[tone],
        className,
      )}
    >
      {icon && <span className="w-3 h-3 shrink-0">{icon}</span>}
      {children}
    </span>
  )
}

// ── Classification chip ───────────────────────────────────────────────────────

type ClassConfig = {
  tone: NonNullable<ChipProps['tone']>
  icon: ReactNode
  label: string
}

const CLASSIFICATION_MAP: Record<FindingClassification | 'needs_review', ClassConfig> = {
  damage:             { tone: 'rose',    icon: <AlertTriangle className="w-3 h-3" />, label: 'Damage' },
  wear:               { tone: 'slate',   icon: <Hourglass className="w-3 h-3" />,     label: 'Normal wear' },
  pre_existing:       { tone: 'sky',     icon: <History className="w-3 h-3" />,        label: 'Already there' },
  owner_responsibility:{ tone: 'violet', icon: <ShieldCheck className="w-3 h-3" />,   label: "Owner's repair" },
  none:               { tone: 'emerald', icon: <CheckCircle2 className="w-3 h-3" />,  label: 'No change' },
  needs_review:       { tone: 'amber',   icon: <Eye className="w-3 h-3" />,            label: 'Needs review' },
}

interface ClassificationChipProps {
  classification: FindingClassification | 'needs_review'
  className?: string
}

export function ClassificationChip({ classification, className }: ClassificationChipProps) {
  const cfg = CLASSIFICATION_MAP[classification] ?? CLASSIFICATION_MAP.none
  return (
    <Chip tone={cfg.tone} icon={cfg.icon} className={className}>
      {cfg.label}
    </Chip>
  )
}

// ── Status pill for inspections ───────────────────────────────────────────────

import { Lock } from 'lucide-react'
import type { InspectionStatus } from '../../api'

const STATUS_MAP: Record<InspectionStatus, { tone: NonNullable<ChipProps['tone']>; label: string; icon?: ReactNode }> = {
  draft:               { tone: 'slate',   label: 'Draft' },
  awaiting_signatures: { tone: 'amber',   label: 'Awaiting signatures' },
  locked:              { tone: 'emerald', label: 'Sealed', icon: <Lock className="w-3 h-3" /> },
}

export function StatusPill({ status }: { status: InspectionStatus }) {
  const cfg = STATUS_MAP[status] ?? STATUS_MAP.draft
  return (
    <Chip tone={cfg.tone} icon={cfg.icon}>
      {cfg.label}
    </Chip>
  )
}
