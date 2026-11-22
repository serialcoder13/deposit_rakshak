import clsx from 'clsx'
import type { ReactNode } from 'react'
import {
  AlertTriangle,
  Hourglass,
  History,
  ShieldCheck,
  Eye,
  CheckCircle2,
  Lock,
  PenLine,
  Camera,
  type LucideIcon,
} from 'lucide-react'
import type { FindingClassification, FindingStatus, InspectionStatus, Stage } from '../../api'
import { STAGE_INFO, stageTone, type StageTone } from '../../lib/journey'

export type ChipTone = StageTone

const toneClasses: Record<ChipTone, string> = {
  rose: 'bg-rose-50 text-rose-700 ring-rose-200/70',
  slate: 'bg-slate-100 text-slate-600 ring-slate-200/70',
  sky: 'bg-sky-50 text-sky-700 ring-sky-200/70',
  violet: 'bg-violet-50 text-violet-700 ring-violet-200/70',
  amber: 'bg-amber-50 text-amber-700 ring-amber-200/70',
  emerald: 'bg-emerald-50 text-emerald-700 ring-emerald-200/70',
  indigo: 'bg-indigo-50 text-indigo-700 ring-indigo-200/70',
  teal: 'bg-teal-50 text-teal-700 ring-teal-200/70',
}

interface ChipProps {
  children: ReactNode
  tone?: ChipTone
  icon?: LucideIcon
  className?: string
  pulse?: boolean
}

export function Chip({ children, tone = 'slate', icon: Icon, className, pulse }: ChipProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 h-6 px-2.5 rounded-full text-xs font-semibold ring-1 whitespace-nowrap',
        toneClasses[tone],
        className,
      )}
    >
      {pulse && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full rounded-full bg-current opacity-60 animate-ping" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
        </span>
      )}
      {Icon && <Icon className="w-3.5 h-3.5 shrink-0" />}
      {children}
    </span>
  )
}

const CLASSIFICATION: Record<FindingClassification | 'needs_review', { tone: ChipTone; icon: LucideIcon; label: string }> = {
  damage: { tone: 'rose', icon: AlertTriangle, label: 'Damage' },
  wear: { tone: 'slate', icon: Hourglass, label: 'Normal wear' },
  pre_existing: { tone: 'sky', icon: History, label: 'Already there' },
  owner_responsibility: { tone: 'violet', icon: ShieldCheck, label: "Owner's repair" },
  none: { tone: 'emerald', icon: CheckCircle2, label: 'No change' },
  needs_review: { tone: 'amber', icon: Eye, label: 'Needs review' },
}

export function ClassificationChip({
  classification,
  className,
}: {
  classification: FindingClassification | 'needs_review'
  className?: string
}) {
  const cfg = CLASSIFICATION[classification] ?? CLASSIFICATION.none
  return (
    <Chip tone={cfg.tone} icon={cfg.icon} className={className}>
      {cfg.label}
    </Chip>
  )
}

const INSPECTION: Record<InspectionStatus, { tone: ChipTone; label: string; icon: LucideIcon }> = {
  draft: { tone: 'slate', label: 'In progress', icon: Camera },
  awaiting_signatures: { tone: 'amber', label: 'Awaiting signatures', icon: PenLine },
  locked: { tone: 'emerald', label: 'Sealed', icon: Lock },
}

export function StatusPill({ status }: { status: InspectionStatus }) {
  const cfg = INSPECTION[status] ?? INSPECTION.draft
  return (
    <Chip tone={cfg.tone} icon={cfg.icon}>
      {cfg.label}
    </Chip>
  )
}

export function StageChip({ stage }: { stage: Stage }) {
  const live = stage === 'ai_check'
  return (
    <Chip tone={stageTone(stage)} pulse={live}>
      {STAGE_INFO[stage]?.short ?? stage}
    </Chip>
  )
}

const FINDING_STATUS: Record<FindingStatus, { tone: ChipTone; label: string }> = {
  proposed: { tone: 'slate', label: 'Awaiting tenant' },
  needs_review: { tone: 'amber', label: 'Needs review' },
  accepted: { tone: 'emerald', label: 'Accepted' },
  disputed: { tone: 'amber', label: 'Disputed' },
}

export function FindingStatusChip({ status }: { status: FindingStatus }) {
  const cfg = FINDING_STATUS[status] ?? FINDING_STATUS.proposed
  return <Chip tone={cfg.tone}>{cfg.label}</Chip>
}
