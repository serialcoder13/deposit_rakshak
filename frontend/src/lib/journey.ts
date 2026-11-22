import type { Role, Stage } from '../api'

export interface StageInfo {
  label: string
  short: string
  /** What this stage means for each role, shown in the journey stepper */
  owner: string
  tenant: string
}

export const STAGE_INFO: Record<Stage, StageInfo> = {
  invite_pending: {
    label: 'Invite',
    short: 'Invite sent',
    owner: 'Your tenant accepts the invite on their phone.',
    tenant: 'Accept the invite from your owner.',
  },
  move_in_capture: {
    label: 'Move-in photos',
    short: 'Move-in photos',
    owner: 'Walk the flat and take one photo per spot.',
    tenant: 'Your owner photographs the flat, spot by spot.',
  },
  move_in_signing: {
    label: 'Review and sign',
    short: 'Signing',
    owner: 'Both of you check the photos and sign.',
    tenant: 'Check every photo, add notes for anything already there, then sign.',
  },
  living: {
    label: 'Living',
    short: 'Protected',
    owner: 'The move-in record is sealed. Issues your tenant reports show here.',
    tenant: 'Your deposit is protected. Report leaks or damage as they happen.',
  },
  move_out_capture: {
    label: 'Move-out photos',
    short: 'Move-out',
    owner: 'Retake each spot, lined up with the move-in photo.',
    tenant: 'Your owner retakes each spot at move-out.',
  },
  ai_check: {
    label: 'AI check',
    short: 'AI check',
    owner: 'The AI compares before and after, spot by spot.',
    tenant: 'The AI compares before and after, spot by spot.',
  },
  review: {
    label: 'Review findings',
    short: 'Review',
    owner: 'Check each finding. You can adjust a cost with a reason.',
    tenant: 'Accept or dispute each finding.',
  },
  settled: {
    label: 'Settled',
    short: 'Settled',
    owner: 'Everything is agreed. Pay the refund.',
    tenant: 'Everything is agreed. Your refund is due.',
  },
}

export type StageTone = 'indigo' | 'teal' | 'amber' | 'violet' | 'emerald' | 'slate' | 'rose' | 'sky'

export function stageTone(stage: Stage): StageTone {
  switch (stage) {
    case 'invite_pending':
      return 'amber'
    case 'move_in_capture':
    case 'move_out_capture':
      return 'indigo'
    case 'move_in_signing':
      return 'violet'
    case 'living':
      return 'teal'
    case 'ai_check':
      return 'sky'
    case 'review':
      return 'amber'
    case 'settled':
      return 'emerald'
  }
}

export function stageDescription(stage: Stage, role: Role): string {
  return STAGE_INFO[stage][role]
}

export function whatsappUrl(text: string): string {
  return `https://wa.me/?text=${encodeURIComponent(text)}`
}

export function inviteText(ownerName: string, address: string): string {
  const who = ownerName ? `${ownerName} has` : 'Your owner has'
  return (
    `${who} invited you to Deposit Rakshak for ${address}. ` +
    `It keeps a sealed photo record of the flat so your deposit is settled fairly. ` +
    `Sign in with this phone number at ${window.location.origin}`
  )
}
