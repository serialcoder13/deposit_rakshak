/**
 * api.ts — Typed fetch wrapper for all backend API calls.
 *
 * JWT is stored in localStorage under "dr_token" (acceptable for a demo;
 * see SPEC §11: "a JWT in memory with localStorage for the demo").
 *
 * Types mirror backend/app/schemas.py and backend/app/models.py.
 */

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------

export function getToken(): string | null {
  return localStorage.getItem('dr_token')
}

export function setToken(token: string): void {
  localStorage.setItem('dr_token', token)
}

export function clearToken(): void {
  localStorage.removeItem('dr_token')
}

// ---------------------------------------------------------------------------
// Base fetch with auth header
// ---------------------------------------------------------------------------

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> ?? {}),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(path, { ...options, headers })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status} ${res.statusText}: ${body}`)
  }
  return res.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// Enums (match models.py)
// ---------------------------------------------------------------------------

export type InspectionType = 'move_in' | 'checkin' | 'move_out'
export type InspectionStatus = 'draft' | 'awaiting_signatures' | 'locked'
export type FindingClassification = 'damage' | 'wear' | 'pre_existing' | 'owner_responsibility' | 'none'
export type FindingStatus = 'proposed' | 'needs_review' | 'accepted' | 'disputed'
export type AgentRunStatus = 'running' | 'done' | 'failed'
export type AgentStepKind = 'thought' | 'tool_call' | 'tool_result' | 'error' | 'done' | 'failed'
export type ChangeType = 'stain' | 'crack' | 'hole' | 'broken' | 'missing' | 'discoloration' | 'scuff' | 'none'
export type MaintenanceCategory = 'seepage' | 'plumbing' | 'electrical' | 'structural' | 'other'

// ---------------------------------------------------------------------------
// Response types (mirror schemas.py)
// ---------------------------------------------------------------------------

export interface User {
  id: string
  phone: string
  name: string
}

export interface TenancyRole {
  tenancy_id: string
  role: 'owner' | 'tenant'
}

export interface MeResponse extends User {
  tenancies: TenancyRole[]
}

export interface SlotNote {
  id: string
  slot_id: string
  author_id: string
  author_name: string
  text: string
  created_at: string
}

export interface SlotPhoto {
  id: string
  url: string
  sha256: string
  captured_at: string
  taken_by: string
}

export interface SlotDetail {
  id: string
  label: string
  guidance: string
  order: number
  item_id: string | null
  photo: SlotPhoto | null
  notes: SlotNote[]
  captured: boolean
}

export interface InspectionDetail {
  id: string
  tenancy_id: string
  type: InspectionType
  status: InspectionStatus
  signed_by_owner_at: string | null
  signed_by_tenant_at: string | null
  lock_hash: string | null
  slots: SlotDetail[]
}

export interface CostBreakdown {
  rate_inr: number
  quantity: number
  depreciation_factor: number
  est_cost: number
  owner_override_cost: number | null
  owner_note: string | null
}

export interface FindingOut {
  id: string
  run_id: string
  slot_id: string
  slot_label: string
  item_id: string
  item_type: string
  before_photo_url: string | null
  after_photo_url: string | null
  change_type: ChangeType
  classification: FindingClassification
  severity: number
  confidence: number
  region_description: string
  reasoning: string
  cited_evidence: string[]
  cost: CostBreakdown
  status: FindingStatus
  tenant_note: string | null
  owner_note: string | null
}

export interface TotalsOut {
  damage_pct: number
  proposed: number
  agreed: number
  disputed: number
  in_dispute: number
  refund_due: number
  deposit: number
}

export interface RunSummaryOut {
  run_id: string
  status: AgentRunStatus
  started_at: string
  finished_at: string | null
  summary_en: string | null
  summary_kn: string | null
}

export interface MaintenanceReportOut {
  id: string
  slot_id: string | null
  item_id: string | null
  description: string
  reported_at: string
  category: MaintenanceCategory
}

export interface TenancyReport {
  tenancy_id: string
  property_score: number
  damage_pct: number
  totals: TotalsOut
  findings: FindingOut[]
  maintenance_reports: MaintenanceReportOut[]
  latest_run: RunSummaryOut | null
}

/** SSE event shape (SPEC §7, BOB_PLAYBOOK integration contract) */
export interface AgentStepEvent {
  seq: number
  kind: AgentStepKind
  label: string
  tool_name: string | null
  payload: unknown
}

export interface InspectionSummary {
  id: string
  type: InspectionType
  status: InspectionStatus
}

export interface TenancyDetail {
  id: string
  property_id: string
  owner_id: string
  tenant_id: string | null
  start_date: string
  deposit: number
  monthly_rent: number
  invite_code: string
  inspections: InspectionSummary[]
  maintenance_reports: MaintenanceReportOut[]
  latest_run: { id: string; status: AgentRunStatus; started_at: string; finished_at: string | null } | null
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

export const api = {
  // Auth
  otpRequest: (phone: string) =>
    apiFetch<{ ok: boolean; hint: string }>('/api/auth/otp/request', {
      method: 'POST',
      body: JSON.stringify({ phone }),
    }),

  otpVerify: (phone: string, otp: string) =>
    apiFetch<{ token: string; user: User }>('/api/auth/otp/verify', {
      method: 'POST',
      body: JSON.stringify({ phone, otp }),
    }),

  me: () => apiFetch<MeResponse>('/api/me'),

  // Tenancy
  getTenancy: (id: string) => apiFetch<TenancyDetail>(`/api/tenancies/${id}`),
  getReport: (id: string) => apiFetch<TenancyReport>(`/api/tenancies/${id}/report`),
  startCompare: (id: string) => apiFetch<{ run_id: string }>(`/api/tenancies/${id}/compare`, { method: 'POST' }),

  createInspection: (tenancyId: string, type: InspectionType) =>
    apiFetch<{ id: string; type: string; status: string }>(`/api/tenancies/${tenancyId}/inspections`, {
      method: 'POST',
      body: JSON.stringify({ type }),
    }),

  fileIssue: (tenancyId: string, body: { description: string; category: MaintenanceCategory; slot_id?: string; item_id?: string }) =>
    apiFetch<{ id: string; ok: boolean }>(`/api/tenancies/${tenancyId}/issues`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  // Inspections
  getInspection: (id: string) => apiFetch<InspectionDetail>(`/api/inspections/${id}`),

  addNote: (inspectionId: string, slot_id: string, text: string) =>
    apiFetch<{ id: string; ok: boolean }>(`/api/inspections/${inspectionId}/notes`, {
      method: 'POST',
      body: JSON.stringify({ slot_id, text }),
    }),

  signInspection: (inspectionId: string) =>
    apiFetch<{ status: string; lock_hash: string | null }>(`/api/inspections/${inspectionId}/sign`, {
      method: 'POST',
    }),

  uploadPhoto: (
    inspectionId: string,
    formData: FormData,
  ) => {
    const token = getToken()
    return fetch(`/api/inspections/${inspectionId}/photos`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    }).then(async (res) => {
      if (!res.ok) throw new Error(await res.text())
      return res.json() as Promise<{ id: string; sha256: string; url: string }>
    })
  },

  // Findings
  patchFinding: (
    id: string,
    body: { status?: FindingStatus; tenant_note?: string; owner_override_cost?: number; owner_note?: string },
  ) =>
    apiFetch<{ id: string; status: FindingStatus; ok: boolean }>(`/api/findings/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
}
