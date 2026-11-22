/**
 * HomePage.tsx — Screen 2 (SPEC §11)
 * Owner: properties and tenancies.
 * Tenant: their tenancy with a status timeline.
 */
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api, clearToken } from '../api'
import { toast } from 'sonner'

export default function HomePage() {
  const navigate = useNavigate()
  const { data: me, isLoading, error, refetch } = useQuery({ queryKey: ['me'], queryFn: api.me, refetchInterval: 3000 })

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

      <div className="px-5 py-5 space-y-4 max-w-md mx-auto">
        {me.pending_invites?.map(inv => (
          <div key={inv.tenancy_id} className="rounded-3xl p-5 text-white bg-gradient-to-br from-indigo-600 via-violet-600 to-fuchsia-500 shadow-lg">
            <div className="text-sm text-white/80">{inv.owner_name} invited you</div>
            <div className="font-display text-lg font-bold mt-1">{inv.address}</div>
            <div className="text-sm text-white/80 mt-1">Rent ₹{inv.monthly_rent.toLocaleString('en-IN')} · Deposit ₹{inv.deposit.toLocaleString('en-IN')}</div>
            <div className="flex gap-2 mt-4">
              <button className="flex-1 h-12 rounded-2xl bg-white text-indigo-700 font-semibold"
                onClick={async () => { try { await api.acceptInvite(inv.tenancy_id); toast.success('Invite accepted'); refetch() } catch (e: any) { toast.error(e?.message || 'Could not accept') } }}>Accept</button>
              <button className="flex-1 h-12 rounded-2xl bg-white/15 border border-white/30 font-semibold"
                onClick={async () => { try { await api.declineInvite(inv.tenancy_id); refetch() } catch (e: any) { toast.error(e?.message || 'Could not decline') } }}>Decline</button>
            </div>
          </div>
        ))}

        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-bold text-slate-900">My homes</h2>
          <button onClick={() => navigate('/properties/new')} className="h-10 px-4 rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white text-sm font-semibold">+ Add property</button>
        </div>

        {me.tenancies.length === 0 && !me.pending_invites?.length ? (
          <div className="grid gap-3">
            <button onClick={() => navigate('/properties/new')} className="text-left bg-white rounded-3xl p-5 shadow-[0_8px_30px_rgba(15,23,42,.08)]">
              <div className="font-display font-semibold text-slate-900">I own a flat</div>
              <div className="text-sm text-slate-500 mt-1">Add it and invite your tenant</div>
            </button>
            <div className="bg-white rounded-3xl p-5 shadow-[0_8px_30px_rgba(15,23,42,.08)]">
              <div className="font-display font-semibold text-slate-900">I'm renting</div>
              <div className="text-sm text-slate-500 mt-1">Ask your owner to invite {me.phone}. The invite will appear here.</div>
            </div>
          </div>
        ) : (
          me.tenancies.map(t => (
            <button key={t.tenancy_id} onClick={() => navigate(`/tenancies/${t.tenancy_id}`)}
              className="w-full text-left bg-white rounded-3xl p-5 shadow-[0_8px_30px_rgba(15,23,42,.08)]">
              <div className="flex items-center justify-between">
                <span className="font-display font-semibold text-slate-900">{t.address || 'My home'}</span>
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${t.role === 'owner' ? 'bg-indigo-50 text-indigo-700' : 'bg-teal-50 text-teal-700'}`}>{t.role === 'owner' ? 'Owner' : 'Tenant'}</span>
              </div>
              <div className="text-sm text-slate-500 mt-1">{t.role === 'owner' ? 'Tenant' : 'Owner'}: {t.other_party_name} · Deposit ₹{t.deposit.toLocaleString('en-IN')}</div>
              <div className="mt-3 rounded-2xl bg-violet-50 px-4 py-3 flex items-center justify-between">
                <span className="text-sm font-medium text-violet-800">{t.next_action.title}</span>
                <span className="text-sm font-semibold text-violet-700">{t.next_action.cta} →</span>
              </div>
            </button>
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
