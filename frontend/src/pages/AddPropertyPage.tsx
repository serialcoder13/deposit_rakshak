/**
 * AddPropertyPage.tsx: owner adds a flat (address, layout preset, item age)
 * and invites the tenant by phone. Backend: POST /api/properties, POST /api/properties/{id}/tenancies.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { api } from '../api'

const input = 'w-full h-12 rounded-2xl border border-slate-200 bg-white px-4 text-base outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100'
const label = 'block text-sm font-medium text-slate-600 mb-1.5'

export default function AddPropertyPage() {
  const navigate = useNavigate()
  const { data: presets } = useQuery({ queryKey: ['presets'], queryFn: api.presets })
  const [address, setAddress] = useState('')
  const [city, setCity] = useState('Bengaluru')
  const [preset, setPreset] = useState('1BHK')
  const [age, setAge] = useState(3)
  const [phone, setPhone] = useState('')
  const [tenantName, setTenantName] = useState('')
  const [rent, setRent] = useState('')
  const [deposit, setDeposit] = useState('')
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10))
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState<{ phone: string } | null>(null)

  const months = Number(rent) > 0 && Number(deposit) > 0 ? (Number(deposit) / Number(rent)).toFixed(1) : null

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    if (address.trim().length < 3) return toast.error('Enter the flat address')
    if (phone.replace(/\D/g, '').length !== 10) return toast.error("Enter the tenant's 10-digit mobile number")
    if (!(Number(rent) > 0) || !(Number(deposit) > 0)) return toast.error('Enter rent and deposit')
    setBusy(true)
    try {
      const prop = await api.createProperty({ address, city, preset, item_age_years: age })
      await api.inviteTenant(prop.id, {
        tenant_phone: phone, tenant_name: tenantName || undefined,
        deposit: Number(deposit), monthly_rent: Number(rent), start_date: startDate,
      })
      setDone({ phone: phone.replace(/\D/g, '') })
    } catch (err: any) {
      toast.error(err?.message || 'Could not add the property')
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    const text = encodeURIComponent(
      `You're invited to Deposit Rakshak for ${address}. Open ${window.location.origin} and log in with this number to accept.`,
    )
    return (
      <div className="min-h-dvh max-w-md mx-auto px-5 py-10 flex flex-col items-center text-center gap-5">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-indigo-600 via-violet-600 to-fuchsia-500 flex items-center justify-center text-white text-4xl">✓</div>
        <h1 className="font-display text-2xl font-bold text-slate-900">Property added</h1>
        <p className="text-slate-500">Invite sent to {done.phone.slice(0, 5)} {done.phone.slice(5)}. They'll see it when they log in with that number.</p>
        <a href={`https://wa.me/?text=${text}`} target="_blank" rel="noreferrer"
           className="w-full h-14 rounded-2xl bg-[#25D366] text-white font-semibold flex items-center justify-center">Share on WhatsApp</a>
        <button onClick={() => navigate('/')} className="w-full h-14 rounded-2xl border border-slate-200 bg-white font-semibold text-slate-800">Back to home</button>
      </div>
    )
  }

  return (
    <div className="min-h-dvh max-w-md mx-auto pb-10">
      <div className="bg-gradient-to-br from-indigo-600 via-violet-600 to-fuchsia-500 text-white px-5 pt-6 pb-8 rounded-b-3xl">
        <button onClick={() => navigate(-1)} className="text-white/80 text-sm mb-3">← Back</button>
        <h1 className="font-display text-2xl font-bold">Add your flat</h1>
        <p className="text-white/80 text-sm mt-1">Set it up and invite your tenant in one go.</p>
      </div>

      <form onSubmit={submit} className="px-5 -mt-4 space-y-5">
        <section className="bg-white rounded-3xl shadow-[0_8px_30px_rgba(15,23,42,.08)] p-5 space-y-4">
          <h2 className="font-display font-semibold text-slate-900">1 · The flat</h2>
          <div><span className={label}>Address</span>
            <input className={input} value={address} onChange={e => setAddress(e.target.value)} placeholder="Flat 4B, 12th Cross, Koramangala" /></div>
          <div><span className={label}>City</span>
            <input className={input} value={city} onChange={e => setCity(e.target.value)} /></div>
        </section>

        <section className="bg-white rounded-3xl shadow-[0_8px_30px_rgba(15,23,42,.08)] p-5 space-y-4">
          <h2 className="font-display font-semibold text-slate-900">2 · Layout</h2>
          <div className="grid grid-cols-3 gap-2">
            {(presets ?? []).map(p => (
              <button type="button" key={p.key} onClick={() => setPreset(p.key)}
                className={`rounded-2xl border p-3 text-left transition ${preset === p.key ? 'border-indigo-500 bg-indigo-50 ring-2 ring-indigo-100' : 'border-slate-200 bg-white'}`}>
                <div className="font-semibold text-slate-900 text-sm">{p.key}</div>
                <div className="text-xs text-slate-500">{p.slot_count} photo spots</div>
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-500">
            {presets?.find(p => p.key === preset)?.rooms.map(r => r.name).join(' · ')}
          </p>
          <div><span className={label}>How old are the paint and furniture? ({age} {age === 1 ? 'year' : 'years'})</span>
            <input type="range" min={0} max={15} value={age} onChange={e => setAge(Number(e.target.value))} className="w-full accent-indigo-600" /></div>
        </section>

        <section className="bg-white rounded-3xl shadow-[0_8px_30px_rgba(15,23,42,.08)] p-5 space-y-4">
          <h2 className="font-display font-semibold text-slate-900">3 · Invite your tenant</h2>
          <div><span className={label}>Tenant's mobile number</span>
            <div className="flex gap-2"><span className="h-12 px-3 rounded-2xl border border-slate-200 bg-slate-50 flex items-center text-slate-600">+91</span>
              <input className={input} inputMode="numeric" maxLength={10} value={phone} onChange={e => setPhone(e.target.value.replace(/\D/g, ''))} placeholder="10-digit number" /></div></div>
          <div><span className={label}>Tenant's name (optional)</span>
            <input className={input} value={tenantName} onChange={e => setTenantName(e.target.value)} /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><span className={label}>Monthly rent (₹)</span>
              <input className={input} inputMode="numeric" value={rent} onChange={e => setRent(e.target.value.replace(/\D/g, ''))} /></div>
            <div><span className={label}>Deposit (₹)</span>
              <input className={input} inputMode="numeric" value={deposit} onChange={e => setDeposit(e.target.value.replace(/\D/g, ''))} /></div>
          </div>
          {months && <p className="text-sm text-violet-700">= {months} months' rent</p>}
          <div><span className={label}>Start date</span>
            <input type="date" className={input} value={startDate} onChange={e => setStartDate(e.target.value)} /></div>
        </section>

        <button disabled={busy} className="w-full h-14 rounded-2xl bg-gradient-to-r from-indigo-600 via-violet-600 to-fuchsia-500 text-white font-semibold disabled:opacity-60">
          {busy ? 'Adding…' : 'Add flat and send invite'}
        </button>
      </form>
    </div>
  )
}
