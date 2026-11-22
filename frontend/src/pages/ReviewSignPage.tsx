/**
 * ReviewSignPage.tsx — Screen 5 (SPEC §11)
 * Grid of slot photos with notes. Sign button. Lock badge after both sign.
 */
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api'

export default function ReviewSignPage() {
  const { inspectionId } = useParams<{ inspectionId: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [signing, setSigning] = useState(false)
  const [noteInputs, setNoteInputs] = useState<Record<string, string>>({})

  const { data: inspection, isLoading } = useQuery({
    queryKey: ['inspection', inspectionId],
    queryFn: () => api.getInspection(inspectionId!),
    refetchInterval: 5000,
  })

  if (isLoading || !inspection) return <div style={styles.center}>Loading…</div>

  const isLocked = inspection.status === 'locked'
  const allCaptured = inspection.slots.every(s => s.captured)

  async function handleSign() {
    setSigning(true)
    try {
      await api.signInspection(inspectionId!)
      qc.invalidateQueries({ queryKey: ['inspection', inspectionId] })
    } finally {
      setSigning(false)
    }
  }

  async function handleAddNote(slotId: string) {
    const text = noteInputs[slotId]?.trim()
    if (!text) return
    await api.addNote(inspectionId!, slotId, text)
    setNoteInputs(prev => ({ ...prev, [slotId]: '' }))
    qc.invalidateQueries({ queryKey: ['inspection', inspectionId] })
  }

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <button onClick={() => navigate(-1)} style={styles.backBtn}>← Back</button>
        <h2 style={{ margin: 0 }}>Review &amp; Sign</h2>
        <div />
      </div>

      {isLocked && (
        <div style={styles.lockBadge}>
          🔒 Locked · {inspection.lock_hash?.slice(0, 8)} · Owner: {inspection.signed_by_owner_at?.slice(0, 10)} · Tenant: {inspection.signed_by_tenant_at?.slice(0, 10)}
        </div>
      )}

      <div style={styles.body}>
        {inspection.slots.map(slot => (
          <div key={slot.id} style={styles.slotCard}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontWeight: 600 }}>{slot.label}</span>
              <span style={{ color: slot.captured ? '#059669' : '#dc2626', fontSize: 13 }}>{slot.captured ? '✓ Captured' : '⚠ No photo'}</span>
            </div>

            {slot.photo && (
              <img src={slot.photo.url} alt={slot.label} style={{ width: '100%', borderRadius: 8, objectFit: 'cover', maxHeight: 200 }} />
            )}

            {slot.notes.map(n => (
              <div key={n.id} style={styles.noteRow}>
                <span style={{ fontWeight: 600, fontSize: 12, color: '#7c3aed' }}>{n.author_name || 'User'}</span>
                <span style={{ marginLeft: 8, fontSize: 14 }}>{n.text}</span>
              </div>
            ))}

            {!isLocked && (
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <input
                  value={noteInputs[slot.id] ?? ''}
                  onChange={e => setNoteInputs(prev => ({ ...prev, [slot.id]: e.target.value }))}
                  placeholder="Add a note (e.g. chip already here)"
                  style={{ flex: 1, padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 14 }}
                />
                <button onClick={() => handleAddNote(slot.id)} style={styles.smallBtn}>Add</button>
              </div>
            )}
          </div>
        ))}
      </div>

      {!isLocked && (
        <div style={styles.footer}>
          <button
            style={{ ...styles.btn, background: allCaptured ? '#1e40af' : '#9ca3af' }}
            disabled={!allCaptured || signing}
            onClick={handleSign}
          >
            {signing ? 'Signing…' : 'Sign Inspection'}
          </button>
          {!allCaptured && <p style={{ fontSize: 12, color: '#dc2626', margin: '8px 0 0', textAlign: 'center' }}>All slots must have photos before signing.</p>}
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { maxWidth: 480, margin: '0 auto', display: 'flex', flexDirection: 'column', minHeight: '100dvh', fontFamily: 'system-ui, sans-serif' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid #e5e7eb' },
  body: { flex: 1, padding: '16px 20px', overflowY: 'auto' },
  footer: { padding: '16px 20px', borderTop: '1px solid #e5e7eb' },
  lockBadge: { background: '#d1fae5', color: '#065f46', padding: '10px 20px', fontSize: 13, fontWeight: 600 },
  slotCard: { border: '1px solid #e5e7eb', borderRadius: 12, padding: '16px', marginBottom: 12, background: '#fff' },
  noteRow: { background: '#f8f4ff', borderRadius: 8, padding: '8px 12px', marginTop: 8 },
  btn: { width: '100%', padding: '14px', fontSize: 16, fontWeight: 600, color: '#fff', border: 'none', borderRadius: 10, cursor: 'pointer' },
  smallBtn: { padding: '8px 16px', background: '#1e40af', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer', fontSize: 14 },
  backBtn: { background: 'none', border: 'none', fontSize: 16, cursor: 'pointer', color: '#3b82d4' },
  center: { display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', fontFamily: 'system-ui' },
}
