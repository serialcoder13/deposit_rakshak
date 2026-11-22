/**
 * HomePage.tsx — Screen 2 (SPEC §11)
 * Owner: properties and tenancies.
 * Tenant: their tenancy with a status timeline.
 */
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api, clearToken } from '../api'

export default function HomePage() {
  const navigate = useNavigate()
  const { data: me, isLoading, error } = useQuery({ queryKey: ['me'], queryFn: api.me })

  function handleLogout() {
    clearToken()
    navigate('/login')
  }

  if (isLoading) return <div style={styles.center}>Loading…</div>
  if (error || !me) return <div style={styles.center}>Error loading user. <button onClick={handleLogout}>Log out</button></div>

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <h1 style={{ margin: 0, fontSize: 20 }}>Deposit Rakshak</h1>
        <div>
          <span style={{ marginRight: 12, color: '#57606a' }}>{me.name}</span>
          <button onClick={handleLogout} style={styles.linkBtn}>Log out</button>
        </div>
      </div>

      <div style={styles.body}>
        <h2 style={{ marginBottom: 16 }}>My Tenancies</h2>
        {me.tenancies.length === 0 ? (
          <p style={{ color: '#57606a' }}>No tenancies found. Run the seed script.</p>
        ) : (
          me.tenancies.map(t => (
            <div key={t.tenancy_id} style={styles.card} onClick={() => navigate(`/tenancies/${t.tenancy_id}`)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 600, fontSize: 16 }}>Tenancy</span>
                <span style={{ background: t.role === 'owner' ? '#dbeafe' : '#d1fae5', color: t.role === 'owner' ? '#1e40af' : '#065f46', padding: '2px 10px', borderRadius: 12, fontSize: 13, fontWeight: 600 }}>
                  {t.role.toUpperCase()}
                </span>
              </div>
              <p style={{ margin: '8px 0 0', color: '#57606a', fontSize: 14 }}>ID: {t.tenancy_id.slice(0, 8)}…</p>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { maxWidth: 480, margin: '0 auto', fontFamily: 'system-ui, sans-serif' },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid #e5e7eb' },
  body: { padding: '20px' },
  card: { border: '1px solid #e5e7eb', borderRadius: 12, padding: '16px', marginBottom: 12, cursor: 'pointer', background: '#fff' },
  linkBtn: { background: 'none', border: 'none', color: '#3b82d4', cursor: 'pointer', fontSize: 14 },
  center: { display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', fontFamily: 'system-ui' },
}
