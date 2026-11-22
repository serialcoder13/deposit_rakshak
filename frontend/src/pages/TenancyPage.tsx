/**
 * TenancyPage.tsx — Screen 3 (SPEC §11)
 * Deposit, rent, dates, invite link, list of inspections, Compare button.
 */
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api'

export default function TenancyPage() {
  const { tenancyId } = useParams<{ tenancyId: string }>()
  const navigate = useNavigate()
  const { data, isLoading, error } = useQuery({
    queryKey: ['tenancy', tenancyId],
    queryFn: () => api.getTenancy(tenancyId!),
  })

  if (isLoading) return <div style={styles.center}>Loading…</div>
  if (error || !data) return <div style={styles.center}>Error loading tenancy.</div>

  const hasRunning = data.latest_run?.status === 'running'
  const hasDone = data.latest_run?.status === 'done'

  async function handleCompare() {
    const res = await api.startCompare(tenancyId!)
    navigate(`/runs/${res.run_id}`)
  }

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <button onClick={() => navigate('/')} style={styles.backBtn}>← Back</button>
        <h2 style={{ margin: 0 }}>Tenancy</h2>
        <div />
      </div>

      <div style={styles.body}>
        <div style={styles.card}>
          <Row label="Deposit" value={`₹${data.deposit.toLocaleString()}`} />
          <Row label="Monthly rent" value={`₹${data.monthly_rent.toLocaleString()}`} />
          <Row label="Start date" value={data.start_date} />
          <Row label="Invite code" value={data.invite_code} />
        </div>

        <h3>Inspections</h3>
        {data.inspections.length === 0 ? (
          <p style={{ color: '#57606a' }}>No inspections yet.</p>
        ) : (
          data.inspections.map(i => (
            <div key={i.id} style={styles.card} onClick={() => navigate(`/inspections/${i.id}/review`)}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontWeight: 600 }}>{i.type.replace('_', ' ').toUpperCase()}</span>
                <StatusChip status={i.status} />
              </div>
            </div>
          ))
        )}

        <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <button style={styles.btn} onClick={() => navigate(`/inspections/new/capture?tenancyId=${tenancyId}&type=move_in`)}>
            Start Move-in Capture
          </button>
          <button style={styles.btn} onClick={() => navigate(`/inspections/new/capture?tenancyId=${tenancyId}&type=move_out`)}>
            Start Move-out Capture
          </button>
          {data.inspections.some(i => i.status === 'locked') && (
            <button
              style={{ ...styles.btn, background: hasRunning ? '#9ca3af' : '#7c3aed' }}
              disabled={hasRunning}
              onClick={handleCompare}
            >
              {hasRunning ? 'Agent running…' : 'Compare (Run Agent)'}
            </button>
          )}
          {hasDone && (
            <button style={{ ...styles.btn, background: '#059669' }} onClick={() => navigate(`/tenancies/${tenancyId}/report`)}>
              View Report
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #f3f4f6' }}>
      <span style={{ color: '#57606a' }}>{label}</span>
      <span style={{ fontWeight: 600 }}>{value}</span>
    </div>
  )
}

function StatusChip({ status }: { status: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    draft: { bg: '#f3f4f6', text: '#374151' },
    awaiting_signatures: { bg: '#fef3c7', text: '#92400e' },
    locked: { bg: '#d1fae5', text: '#065f46' },
  }
  const c = colors[status] ?? { bg: '#f3f4f6', text: '#374151' }
  return (
    <span style={{ background: c.bg, color: c.text, padding: '2px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600 }}>
      {status === 'locked' ? '🔒 ' : ''}{status.replace('_', ' ')}
    </span>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { maxWidth: 480, margin: '0 auto', fontFamily: 'system-ui, sans-serif' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid #e5e7eb' },
  body: { padding: '20px' },
  card: { border: '1px solid #e5e7eb', borderRadius: 12, padding: '16px', marginBottom: 12, background: '#fff', cursor: 'pointer' },
  btn: { padding: '14px', fontSize: 16, fontWeight: 600, background: '#1e40af', color: '#fff', border: 'none', borderRadius: 10, cursor: 'pointer' },
  backBtn: { background: 'none', border: 'none', fontSize: 16, cursor: 'pointer', color: '#3b82d4' },
  center: { display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', fontFamily: 'system-ui' },
}
