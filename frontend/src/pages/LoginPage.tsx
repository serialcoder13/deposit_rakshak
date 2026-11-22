/**
 * LoginPage.tsx — Screen 1, Iteration 1 reskin.
 * Design: full-height brand gradient hero + white Card below.
 * Logic: unchanged from the skeleton (OTP request → verify → JWT → Home).
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Phone, KeyRound, ArrowRight } from 'lucide-react'
import { api, setToken } from '../api'
import { Button, Card, GlassCard } from '../components/ui'

export default function LoginPage() {
  const navigate = useNavigate()
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [step, setStep] = useState<'phone' | 'otp'>('phone')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleRequestOtp(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.otpRequest(phone)
      setStep('otp')
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleVerifyOtp(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.otpVerify(phone, otp)
      setToken(res.token)
      navigate('/')
    } catch (err: unknown) {
      setError(String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-dvh flex flex-col">
      {/* ── Brand hero ── */}
      <div className="relative bg-gradient-to-br from-indigo-600 via-violet-600 to-fuchsia-500 px-6 pt-safe flex flex-col items-center justify-center pb-10"
           style={{ minHeight: '44dvh' }}>
        {/* Decorative circle blur */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2 pointer-events-none" />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="flex flex-col items-center text-center z-10"
        >
          {/* Shield logo */}
          <img src="/logo.svg" alt="Deposit Rakshak shield" className="w-20 h-20 mb-5 drop-shadow-xl" />
          <h1 className="text-3xl font-display font-extrabold text-white leading-tight">
            Deposit Rakshak
          </h1>
          <p className="mt-2 text-white/80 text-base font-medium">
            Your deposit, protected.
          </p>
        </motion.div>
      </div>

      {/* ── Form card ── */}
      <div className="flex-1 bg-page px-4 -mt-6 pb-safe">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.15, ease: 'easeOut' }}
        >
          <Card className="shadow-soft-lg">
            {step === 'phone' ? (
              <form onSubmit={handleRequestOtp} className="space-y-5">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Phone number
                  </label>
                  <div className="flex items-center gap-0 border border-slate-200 rounded-2xl overflow-hidden focus-within:ring-2 focus-within:ring-indigo-500 bg-white">
                    <span className="px-4 py-3.5 text-sm font-semibold text-slate-500 bg-slate-50 border-r border-slate-200 select-none">
                      +91
                    </span>
                    <input
                      type="tel"
                      value={phone}
                      onChange={e => setPhone(e.target.value.replace(/\D/g, '').slice(0, 10))}
                      placeholder="9999990001"
                      required
                      inputMode="numeric"
                      className="flex-1 px-4 py-3.5 text-base font-display text-slate-900 outline-none bg-white tabular-nums"
                    />
                  </div>
                </div>

                {error && <p className="text-sm text-danger">{error}</p>}

                <Button type="submit" size="lg" loading={loading} icon={<Phone className="w-4 h-4" />}>
                  Send OTP
                </Button>
              </form>
            ) : (
              <form onSubmit={handleVerifyOtp} className="space-y-5">
                {/* Demo hint */}
                <div className="flex items-center gap-3 bg-emerald-50 border border-emerald-200 rounded-2xl px-4 py-3">
                  <KeyRound className="w-4 h-4 text-emerald-600 shrink-0" />
                  <p className="text-sm text-emerald-700">
                    Demo OTP: <span className="font-display font-bold tracking-widest">123456</span>
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">
                    Enter 6-digit OTP
                  </label>
                  <input
                    type="text"
                    value={otp}
                    onChange={e => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="123456"
                    maxLength={6}
                    required
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    className="w-full border border-slate-200 rounded-2xl px-5 py-4 text-3xl font-display tabular-nums tracking-[0.5em] text-slate-900 text-center outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                  />
                </div>

                {error && <p className="text-sm text-danger">{error}</p>}

                <Button type="submit" size="lg" loading={loading} icon={<ArrowRight className="w-4 h-4" />}>
                  Verify &amp; Continue
                </Button>

                <button
                  type="button"
                  onClick={() => { setStep('phone'); setError('') }}
                  className="w-full text-sm text-slate-500 hover:text-slate-700 py-2 transition-colors"
                >
                  ← Change number
                </button>
              </form>
            )}
          </Card>

          {/* Demo quick-login hint */}
          <div className="mt-4 px-1">
            <GlassCard className="bg-white/60 border border-slate-200 !p-4">
              <p className="text-xs text-slate-500 font-semibold uppercase tracking-wide mb-2">Demo accounts</p>
              <div className="flex gap-2">
                <DemoBtn label="Owner (Ravi)" phone="9999990001" onSelect={p => { setPhone(p); setStep('phone') }} />
                <DemoBtn label="Tenant (Meera)" phone="9999990002" onSelect={p => { setPhone(p); setStep('phone') }} />
              </div>
            </GlassCard>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

function DemoBtn({ label, phone, onSelect }: { label: string; phone: string; onSelect: (p: string) => void }) {
  return (
    <button
      type="button"
      onClick={() => onSelect(phone)}
      className="flex-1 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-xl py-2.5 px-3 hover:bg-indigo-50 hover:border-indigo-300 hover:text-indigo-700 transition-colors active:scale-95"
    >
      {label}
    </button>
  )
}
