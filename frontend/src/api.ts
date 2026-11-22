/**
 * api.ts: typed fetch wrapper for the Deposit Rakshak backend.
 * The JWT lives in localStorage under "dr_token".
 */

const TOKEN_KEY = 'dr_token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

/** Error carrying the backend's `detail` text, safe to show to users. */
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function detailText(status: number, body: unknown): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const d = (body as { detail: unknown }).detail
    if (typeof d === 'string') return d
    if (Array.isArray(d) && d.length) {
      const first = d[0] as { msg?: string }
      if (first?.msg) return first.msg.replace(/^Value error, /, '')
    }
  }
  if (status === 401) return 'Your session has ended. Please sign in again.'
  if (status >= 500) return 'Something went wrong on our side. Please try again.'
  return 'Something went wrong. Please try again.'
}

/** Human message for any thrown value. */
export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message
  if (err instanceof TypeError) return 'You seem to be offline. Check your connection.'
  if (err instanceof Error && err.message) return err.message
  return 'Something went wrong. Please try again.'
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'ngrok-skip-browser-warning': 'true',
    ...((options.headers as Record<string, string>) ?? {}),
  }
  if (!(options.body instanceof FormData) && options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(path, { ...options, headers })
  const text = await res.text()
  let body: unknown = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = null
    }
  }
  if (!res.ok) {
    if (res.status === 401 && token) {
      clearToken()
      if (!window.location.pathname.startsWith('/login')) window.location.assign('/login')
    }
    throw new ApiError(res.status, detailText(res.status, body))
  }
  return body as T
}

const json = (method: string, data?: unknown): RequestInit => ({
  method,
  body: data === undefined ? undefined : JSON.stringify(data),
})

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export type Role = 'owner' | 'tenant'
export type InspectionType = 'move_in' | 'checkin' | 'move_out'
export type InspectionStatus = 'draft' | 'awaiting_signatures' | 'locked'
export type FindingClassification = 'damage' | 'wear' | 'pre_existing' | 'owner_responsibility' | 'none'
export type FindingStatus = 'proposed' | 'needs_review' | 'accepted' | 'disputed'
export type AgentRunStatus = 'running' | 'done' | 'failed'
export type AgentStepKind = 'thought' | 'tool_call' | 'tool_result' | 'error' | 'done' | 'failed'
export type MaintenanceCategory = 'seepage' | 'plumbing' | 'electrical' | 'structural' | 'other'
export type CostBasis = 'rate_card' | 'replacement_value' | 'not_charged'

export const STAGES = [
  'invite_pending',
  'move_in_capture',
  'move_in_signing',
  'living',
  'move_out_capture',
  'ai_check',
  'review',
  'settled',
] as const
export type Stage = (typeof STAGES)[number]

// ---------------------------------------------------------------------------
// Shapes
// ---------------------------------------------------------------------------

export interface User {
  id: string
  phone: string
  name: string
}

export interface NextAction {
  title: string
  cta: string
}

export interface TenancySummary {
  tenancy_id: string
  role: Role
  property_id: string
  address: string
  city: string
  deposit: number
  monthly_rent: number
  start_date: string | null
  other_party_name: string | null
  tenant_phone: string
  invite_status: 'pending' | 'accepted'
  stage: Stage
  stage_index: number
  next_action: NextAction
}

export interface PendingInvite {
  tenancy_id: string
  address: string
  city: string
  owner_name: string
  deposit: number
  monthly_rent: number
  start_date: string | null
}

export interface Me extends User {
  is_new_user: boolean
  tenancies: TenancySummary[]
  pending_invites: PendingInvite[]
}

export interface Preset {
  key: string
  rooms: { name: string; slots: string[] }[]
  slot_count: number
}

export interface PropertyCreated {
  id: string
  owner_id: string
  address: string
  city: string
}

export interface TenancyCreated {
  tenancy_id: string
  property_id: string
  tenant_phone: string
  invite_status: string
  invite_code: string
  tenant_already_registered: boolean
}

export interface InspectionSummary {
  id: string
  type: InspectionType
  status: InspectionStatus
  photo_count: number
  slot_count: number
  signed_by_owner_at: string | null
  signed_by_tenant_at: string | null
  lock_hash: string | null
}

export interface MaintenanceReport {
  id: string
  slot_id: string | null
  slot_label?: string | null
  item_id: string | null
  description: string
  reported_at: string
  category: MaintenanceCategory
}

export interface TenancyDetail {
  id: string
  property_id: string
  owner_id: string
  tenant_id: string | null
  start_date: string | null
  deposit: number
  monthly_rent: number
  invite_code: string
  my_role: Role
  address: string
  city: string
  owner_name: string | null
  tenant_name: string | null
  tenant_phone: string
  invite_status: 'pending' | 'accepted'
  stage: Stage
  stage_index: number
  next_action: NextAction
  slots: { id: string; label: string; room: string }[]
  inspections: InspectionSummary[]
  maintenance_reports: MaintenanceReport[]
  latest_run: { id: string; status: AgentRunStatus; started_at: string; finished_at: string | null } | null
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

export interface InspectionSlot {
  id: string
  label: string
  guidance: string
  order: number
  item_id: string | null
  room: string
  captured: boolean
  ghost_url: string | null
  photo: SlotPhoto | null
  notes: SlotNote[]
}

export interface InspectionDetail {
  id: string
  tenancy_id: string
  type: InspectionType
  status: InspectionStatus
  signed_by_owner_at: string | null
  signed_by_tenant_at: string | null
  lock_hash: string | null
  slots: InspectionSlot[]
}

export interface SignResult {
  status: InspectionStatus
  lock_hash: string | null
  signed_by_owner_at: string | null
  signed_by_tenant_at: string | null
}

export interface AgentStep {
  seq: number
  kind: AgentStepKind
  label: string
  tool_name: string | null
  payload: unknown
}

export interface RunSteps {
  run_id: string
  tenancy_id: string
  status: AgentRunStatus
  steps: AgentStep[]
}

export interface Evidence {
  id: string
  kind: 'move_in_note' | 'maintenance_report'
  text: string
  date: string | null
  author: string | null
}

export interface Cost {
  rate_inr: number
  quantity: number
  depreciation_factor: number
  est_cost: number
  owner_override_cost: number | null
  owner_note: string | null
  cost_basis: CostBasis
  effective_cost: number
  item_age_years_at_move_out: number | null
  useful_life_years: number | null
  replacement_cost: number | null
}

export interface Finding {
  id: string
  slot_id: string
  slot_label: string
  room: string | null
  item_type: string
  before_photo_url: string | null
  after_photo_url: string | null
  change_type: string
  classification: FindingClassification
  severity: number
  confidence: number
  region_description: string
  reasoning: string
  evidence: Evidence[]
  bbox_after: [number, number, number, number] | null
  cost: Cost
  status: FindingStatus
  tenant_note: string | null
  owner_note: string | null
}

export interface Totals {
  damage_pct: number
  proposed: number
  agreed: number
  disputed: number
  in_dispute: number
  refund_due: number
  deposit: number
}

export interface Report {
  tenancy_id: string
  my_role: Role
  address: string
  owner_name: string | null
  tenant_name: string | null
  move_in_lock_hash: string | null
  move_out_lock_hash: string | null
  property_score: number
  damage_pct: number
  totals: Totals
  findings: Finding[]
  maintenance_reports: MaintenanceReport[]
  latest_run: {
    run_id: string
    status: AgentRunStatus
    started_at: string
    finished_at: string | null
    summary_en: string | null
    summary_kn: string | null
  } | null
}

// ---------------------------------------------------------------------------
// Calls
// ---------------------------------------------------------------------------

export const api = {
  otpRequest: (phone: string) =>
    request<{ ok: boolean; phone: string; is_new_user: boolean }>('/api/auth/otp/request', json('POST', { phone })),
  otpVerify: (phone: string, otp: string) =>
    request<{ token: string; user: User; is_new_user: boolean }>('/api/auth/otp/verify', json('POST', { phone, otp })),

  me: () => request<Me>('/api/me'),
  updateMe: (name: string) => request<Me>('/api/me', json('PATCH', { name })),

  presets: () => request<Preset[]>('/api/properties/presets'),
  createProperty: (body: { address: string; city: string; preset: string; item_age_years: number }) =>
    request<PropertyCreated>('/api/properties', json('POST', body)),
  inviteTenant: (
    propertyId: string,
    body: { tenant_phone: string; tenant_name?: string; deposit: number; monthly_rent: number; start_date?: string },
  ) => request<TenancyCreated>(`/api/properties/${propertyId}/tenancies`, json('POST', body)),

  tenancy: (id: string) => request<TenancyDetail>(`/api/tenancies/${id}`),
  acceptInvite: (id: string) => request<TenancyDetail>(`/api/tenancies/${id}/accept`, json('POST')),
  declineInvite: (id: string) => request<{ ok: boolean }>(`/api/tenancies/${id}/decline`, json('POST')),
  reportIssue: (id: string, body: { description: string; category: MaintenanceCategory; slot_id?: string }) =>
    request<unknown>(`/api/tenancies/${id}/issues`, json('POST', body)),
  startInspection: (id: string, type: InspectionType) =>
    request<{ id: string; type: InspectionType; status: InspectionStatus; resumed: boolean }>(
      `/api/tenancies/${id}/inspections`,
      json('POST', { type }),
    ),
  compare: (id: string) => request<{ run_id: string }>(`/api/tenancies/${id}/compare`, json('POST')),
  report: (id: string) => request<Report>(`/api/tenancies/${id}/report`),

  inspection: (id: string) => request<InspectionDetail>(`/api/inspections/${id}`),
  uploadPhoto: (id: string, form: FormData) =>
    request<{ id: string; sha256: string; url: string }>(`/api/inspections/${id}/photos`, {
      method: 'POST',
      body: form,
    }),
  addNote: (id: string, slot_id: string, text: string) =>
    request<unknown>(`/api/inspections/${id}/notes`, json('POST', { slot_id, text })),
  sign: (id: string) => request<SignResult>(`/api/inspections/${id}/sign`, json('POST')),

  runSteps: (id: string, after = 0) => request<RunSteps>(`/api/runs/${id}/steps?after=${after}`),

  patchFinding: (
    id: string,
    body: { status?: 'accepted' | 'disputed'; tenant_note?: string; owner_override_cost?: number; owner_note?: string },
  ) => request<{ id: string; status: FindingStatus; ok: boolean }>(`/api/findings/${id}`, json('PATCH', body)),

  // Aliases used by older screens
  getTenancy: (id: string) => request<TenancyDetail>(`/api/tenancies/${id}`),
  getReport: (id: string) => request<Report>(`/api/tenancies/${id}/report`),
  getInspection: (id: string) => request<InspectionDetail>(`/api/inspections/${id}`),
  signInspection: (id: string) => request<SignResult>(`/api/inspections/${id}/sign`, json('POST')),
  startCompare: (id: string) => request<{ run_id: string }>(`/api/tenancies/${id}/compare`, json('POST')),
  createInspection: (id: string, type: InspectionType) =>
    request<{ id: string; type: InspectionType; status: InspectionStatus; resumed: boolean }>(
      `/api/tenancies/${id}/inspections`,
      json('POST', { type }),
    ),
  fileIssue: (id: string, body: { description: string; category: MaintenanceCategory; slot_id?: string }) =>
    request<unknown>(`/api/tenancies/${id}/issues`, json('POST', body)),
}

export type AgentStepEvent = AgentStep
export type FindingOut = Finding
