/**
 * ReportPage.tsx — Screen 7 (SPEC §11)
 * Condition score, damage %, totals bar, finding cards with Accept/Dispute.
 * Polls /report every 3s so both phones stay in sync (SPEC §11).
 */
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api, type FindingOut } from '../api'

const CLASSIFICATION_LABEL: Record<string, string> = {
  damage: '🔴 Damage',
  wear: '🟡 Wear',
  pre_existing: '🔵 Pre-existing',
  owner_responsibility: '🟢 Owner\'s responsibility',
  none: '⚪ No change',
  needs_review: '🟠 Needs review',
}

export default function ReportPage() {
  const { tenancyId } = useParams<{ tenancyId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['report', tenancyId],
    queryFn: () => api.getReport(tenancyId!),
    refetchInterval: 3000,
  })

  const [disputeNotes, setDisputeNotes] = useState<Record<string, string>>({})

  async function handleAccept(id: string) {
    await api.patchFinding(id, { status: 'accepted' })
    qc.invalidateQueries({ queryKey: ['report', tenancyId] })
  }

  async function handleDispute(id: string) {
    await api.patchFinding(id, { status: 'disputed', tenant_note: disputeNotes[id] ?? '' })
    qc.invalidateQueries({ queryKey: ['report', tenancyId] })
  }

  if (isLoading || !data) return <div style={styles.center}>Loading report…</div>

  const { totals } = data

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <button onClick={() => navigate(-1)} style={styles.backBtn}>← Back</button>
        <h2 style={{ margin: 0 }}>Report</h2>
        <button style={styles.settleBtn} onClick={() => navigate(`/tenancies/${tenancyId}/settlement`)}>Settle →</button>
      </div>

      {/* Score dial placeholder */}
      <div style={styles.scoreBanner}>
        <div>
          <div style={{ fontSize: 36, fontWeight: 700 }}>{Math.round(data.property_score)}</div>
          <div style={{ fontSize: 12, color: '#57606a' }}>Condition score</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#dc2626' }}>{data.damage_pct.toFixed(1)}%</div>
          <div style={{ fontSize: 12, color: '#57606a' }}>Damage</div>
        </div>
      </div>

      {/* Totals */}
      <div style={styles.totalsCard}>
        <TotalRow label="Deposit" value={totals.deposit} />
        <TotalRow label="Proposed deduction" value={totals.proposed} />
        <TotalRow label="Agreed deduction" value={totals.agreed} color="#dc2626" />
        <TotalRow label="In dispute" value={totals.in_dispute} color="#d97706" />
        <TotalRow label="Refund due" value={totals.refund_due} color="#059669" bold />
      </div>

      {/* Findings */}
      <div style={styles.body}>
        <h3 style={{ marginBottom: 12 }}>Findings ({data.findings.length})</h3>
        {data.findings.length === 0 && <p style={{ color: '#9ca3af' }}>No findings yet. Run the agent first.</p>}
        {data.findings.map(f => (
          <FindingCard
            key={f.id}
            finding={f}
            disputeNote={disputeNotes[f.id] ?? ''}
            onDisputeNoteChange={text => setDisputeNotes(prev => ({ ...prev, [f.id]: text }))}
            onAccept={() => handleAccept(f.id)}
            onDispute={() => handleDispute(f.id)}
          />
        ))}
      </div>
    </div>
  )
}

function TotalRow({ label, value, color, bold }: { label: string; value: number; color?: string; bold?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f3f4f6' }}>
      <span style={{ color: '#57606a', fontWeight: bold ? 700 : 400 }}>{label}</span>
      <span style={{ fontWeight: bold ? 700 : 600, color: color ?? '#1f2328' }}>₹{value.toLocaleString()}</span>
    </div>
  )
}

function FindingCard({
  finding, disputeNote, onDisputeNoteChange, onAccept, onDispute,
}: {
  finding: FindingOut
  disputeNote: string
  onDisputeNoteChange: (t: string) => void
  onAccept: () => void
  onDispute: () => void
}) {
  const canAct = finding.status === 'proposed' || finding.status === 'needs_review'

  return (
    <div style={cardStyles.card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <span style={{ fontWeight: 600 }}>{finding.slot_label}</span>
        <span style={getChipStyle(finding.classification)}>{CLASSIFICATION_LABEL[finding.classification] ?? finding.classification}</span>
      </div>

      {/* Before / after */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        {finding.before_photo_url && <img src={finding.before_photo_url} alt="before" style={cardStyles.photo} />}
        {finding.after_photo_url && <img src={finding.after_photo_url} alt="after" style={cardStyles.photo} />}
      </div>

      <p style={{ margin: '0 0 4px', fontSize: 14, color: '#374151' }}>{finding.region_description}</p>
      <p style={{ margin: '0 0 8px', fontSize: 13, color: '#57606a' }}>{finding.reasoning}</p>

      {finding.classification === 'damage' && (
        <div style={cardStyles.costBox}>
          <span>Severity {finding.severity} · confidence {(finding.confidence * 100).toFixed(0)}%</span>
          <span style={{ fontWeight: 700, color: '#dc2626' }}>₹{finding.cost.est_cost.toLocaleString()}</span>
        </div>
      )}

      {/* Status chip */}
      <div style={{ marginBottom: 8 }}>
        <span style={{ fontSize: 12, color: '#7c3aed', fontWeight: 600 }}>{finding.status.replace('_', ' ').toUpperCase()}</span>
      </div>

      {/* Accept / Dispute */}
      {canAct && (
        <div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <button onClick={onAccept} style={cardStyles.acceptBtn}>Accept</button>
            <button onClick={onDispute} style={cardStyles.disputeBtn}>Dispute</button>
          </div>
          <input
            value={disputeNote}
            onChange={e => onDisputeNoteChange(e.target.value)}
            placeholder="Reason for dispute (optional)"
            style={cardStyles.noteInput}
          />
        </div>
      )}
    </div>
  )
}

function getChipStyle(classification: string): React.CSSProperties {
  const map: Record<string, string> = { damage: '#fee2e2', wear: '#fef3c7', pre_existing: '#dbeafe', owner_responsibility: '#d1fae5', none: '#f3f4f6' }
  return { background: map[classification] ?? '#f3f4f6', borderRadius: 12, padding: '2px 10px', fontSize: 12, fontWeight: 600 }
}

const styles: Record<string, React.CSSProperties> = {
  page: { maxWidth: 480, margin: '0 auto', display: 'flex', flexDirection: 'column', minHeight: '100dvh', fontFamily: 'system-ui, sans-serif' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid #e5e7eb' },
  scoreBanner: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px', background: '#f7f8fa' },
  totalsCard: { margin: '0 20px 16px', border: '1px solid #e5e7eb', borderRadius: 12, padding: '16px', background: '#fff' },
  body: { flex: 1, padding: '0 20px 20px', overflowY: 'auto' },
  backBtn: { background: 'none', border: 'none', fontSize: 16, cursor: 'pointer', color: '#3b82d4' },
  settleBtn: { background: '#059669', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', cursor: 'pointer', fontWeight: 600 },
  center: { display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', fontFamily: 'system-ui' },
}

const cardStyles: Record<string, React.CSSProperties> = {
  card: { border: '1px solid #e5e7eb', borderRadius: 12, padding: '16px', marginBottom: 12, background: '#fff' },
  photo: { flex: 1, width: '50%', height: 120, objectFit: 'cover', borderRadius: 8 },
  costBox: { display: 'flex', justifyContent: 'space-between', background: '#fef3c7', borderRadius: 8, padding: '8px 12px', marginBottom: 8, fontSize: 13 },
  acceptBtn: { flex: 1, padding: '10px', background: '#059669', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 },
  disputeBtn: { flex: 1, padding: '10px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontWeight: 600 },
  noteInput: { width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 14, boxSizing: 'border-box' as const },
}
