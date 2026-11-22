/**
 * SettlementPage.tsx — Screen 8 (SPEC §11)
 * Final totals, English + Kannada summary, WhatsApp share link.
 */
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { api } from '../api'

export default function SettlementPage() {
  const { tenancyId } = useParams<{ tenancyId: string }>()
  const navigate = useNavigate()
  const [lang, setLang] = useState<'en' | 'kn'>('en')

  const { data, isLoading } = useQuery({
    queryKey: ['report', tenancyId],
    queryFn: () => api.getReport(tenancyId!),
    refetchInterval: 3000,
  })

  if (isLoading || !data) return <div style={styles.center}>Loading…</div>

  const { totals, latest_run } = data
  const summary = lang === 'en' ? latest_run?.summary_en : latest_run?.summary_kn

  const shareText = encodeURIComponent(
    `Deposit Rakshak Settlement\nRefund due: ₹${totals.refund_due.toLocaleString()}\nAgreed deduction: ₹${totals.agreed.toLocaleString()}\n\n${latest_run?.summary_en ?? ''}`
  )
  const whatsappUrl = `https://wa.me/?text=${shareText}`

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <button onClick={() => navigate(-1)} style={styles.backBtn}>← Back</button>
        <h2 style={{ margin: 0 }}>Settlement</h2>
        <div />
      </div>

      <div style={styles.body}>
        {/* Totals */}
        <div style={styles.card}>
          <h3 style={{ margin: '0 0 12px' }}>Final Totals</h3>
          <BigRow label="Deposit" value={totals.deposit} />
          <BigRow label="Agreed deduction" value={totals.agreed} color="#dc2626" />
          <BigRow label="In dispute" value={totals.in_dispute} color="#d97706" />
          <div style={{ borderTop: '2px solid #1e40af', marginTop: 12, paddingTop: 12 }}>
            <BigRow label="Refund due" value={totals.refund_due} color="#059669" bold />
          </div>
        </div>

        {/* Summary */}
        <div style={styles.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Summary</h3>
            <div style={{ display: 'flex', gap: 4 }}>
              <LangBtn label="English" active={lang === 'en'} onClick={() => setLang('en')} />
              <LangBtn label="ಕನ್ನಡ" active={lang === 'kn'} onClick={() => setLang('kn')} />
            </div>
          </div>
          <p style={{ margin: 0, lineHeight: 1.7, color: '#374151', fontSize: 15 }}>
            {summary ?? (lang === 'kn' ? 'ಸಾರಾಂಶ ಇನ್ನೂ ಲಭ್ಯವಿಲ್ಲ. ಮೊದಲು ಏಜೆಂಟ್ ಚಾಲನೆ ಮಾಡಿ.' : 'No summary yet. Run the agent first.')}
          </p>
        </div>

        {/* Share */}
        <a
          href={whatsappUrl}
          target="_blank"
          rel="noopener noreferrer"
          style={styles.whatsappBtn}
        >
          <span style={{ fontSize: 20 }}>📲</span> Share on WhatsApp
        </a>
      </div>
    </div>
  )
}

function BigRow({ label, value, color, bold }: { label: string; value: number; color?: string; bold?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0' }}>
      <span style={{ color: '#57606a', fontWeight: bold ? 700 : 400, fontSize: 16 }}>{label}</span>
      <span style={{ fontWeight: 700, fontSize: 20, color: color ?? '#1f2328' }}>₹{value.toLocaleString()}</span>
    </div>
  )
}

function LangBtn({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{ padding: '4px 12px', borderRadius: 20, border: '1px solid #1e40af', background: active ? '#1e40af' : '#fff', color: active ? '#fff' : '#1e40af', cursor: 'pointer', fontSize: 13, fontWeight: 600 }}
    >
      {label}
    </button>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { maxWidth: 480, margin: '0 auto', display: 'flex', flexDirection: 'column', minHeight: '100dvh', fontFamily: 'system-ui, sans-serif' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid #e5e7eb' },
  body: { flex: 1, padding: '20px' },
  card: { border: '1px solid #e5e7eb', borderRadius: 12, padding: '20px', marginBottom: 16, background: '#fff' },
  whatsappBtn: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, width: '100%', padding: '16px', background: '#25d366', color: '#fff', borderRadius: 12, textDecoration: 'none', fontWeight: 700, fontSize: 18, boxSizing: 'border-box' },
  backBtn: { background: 'none', border: 'none', fontSize: 16, cursor: 'pointer', color: '#3b82d4' },
  center: { display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', fontFamily: 'system-ui' },
}
