import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowRight, Camera, Lock, ScanEye, ShieldCheck } from 'lucide-react'
import { toast } from 'sonner'
import { useQueryClient } from '@tanstack/react-query'
import { api, errorMessage, getToken, setToken } from '../api'
import { Button, Card, OtpInput } from '../components/ui'
import { prettyPhone } from '../lib/format'

const RESEND_SECONDS = 30

export default function LoginPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [step, setStep] = useState<'phone' | 'otp'>('phone')
  const [loading, setLoading] = useState(false)
  const [otpError, setOtpError] = useState(false)
  const [resendIn, setResendIn] = useState(0)

  useEffect(() => {
    if (getToken()) navigate('/', { replace: true })
  }, [navigate])

  useEffect(() => {
    if (resendIn <= 0) return
    const t = setTimeout(() => setResendIn((s) => s - 1), 1000)
    return () => clearTimeout(t)
  }, [resendIn])

  const phoneValid = /^[6-9]\d{9}$/.test(phone)

  async function requestOtp(e?: React.FormEvent) {
    e?.preventDefault()
    if (!phoneValid) {
      toast.error('Enter a valid 10 digit mobile number')
      return
    }
    setLoading(true)
    try {
      await api.otpRequest(phone)
      setOtp('')
      setStep('otp')
      setResendIn(RESEND_SECONDS)
      toast.success(`Code sent to ${prettyPhone(phone)}`)
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function verify(code: string) {
    if (code.length !== 6 || loading) return
    setLoading(true)
    setOtpError(false)
    try {
      const res = await api.otpVerify(phone, code)
      setToken(res.token)
      qc.clear()
      navigate(res.is_new_user || !res.user.name ? '/welcome' : '/', { replace: true })
    } catch (err) {
      setOtpError(true)
      setOtp('')
      toast.error(errorMessage(err))
      setTimeout(() => setOtpError(false), 500)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-dvh flex flex-col">
      <div className="relative overflow-hidden bg-brand-gradient pt-safe">
        <div className="absolute -top-24 -right-16 w-72 h-72 bg-fuchsia-400/30 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-16 w-72 h-72 bg-indigo-400/30 rounded-full blur-3xl pointer-events-none" />
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="relative max-w-md mx-auto px-6 pt-14 pb-16 flex flex-col items-center text-center"
        >
          <div className="w-20 h-20 rounded-3xl bg-white/15 border border-white/25 backdrop-blur-xl flex items-center justify-center shadow-2xl animate-float">
            <img src="/logo.svg" alt="" className="w-14 h-14" />
          </div>
          <h1 className="mt-5 text-3xl font-extrabold text-white tracking-tight">Deposit Rakshak</h1>
          <p className="mt-2 text-white/85 text-base">A sealed photo record of your flat, so the deposit comes back fair.</p>
          <div className="mt-6 flex flex-wrap justify-center items-center gap-2 text-white/90 text-xs font-semibold">
            {[
              { icon: Camera, t: 'Guided photos' },
              { icon: Lock, t: 'Sealed by both' },
              { icon: ScanEye, t: 'AI check' },
            ].map(({ icon: Icon, t }) => (
              <span key={t} className="inline-flex items-center gap-1 h-8 px-3 rounded-full bg-white/15 border border-white/20 backdrop-blur">
                <Icon className="w-3.5 h-3.5" />
                {t}
              </span>
            ))}
          </div>
        </motion.div>
      </div>

      <div className="flex-1 px-4 -mt-8 pb-safe-8">
        <motion.div
          className="max-w-md mx-auto"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1, ease: 'easeOut' }}
        >
          <Card className="shadow-soft-lg p-6">
            <AnimatePresence mode="wait" initial={false}>
              {step === 'phone' ? (
                <motion.form
                  key="phone"
                  onSubmit={requestOtp}
                  initial={{ opacity: 0, x: -16 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -16 }}
                  className="space-y-5"
                >
                  <div>
                    <h2 className="text-xl font-bold text-slate-900">Sign in or sign up</h2>
                    <p className="text-sm text-slate-500 mt-1">We will text a 6 digit code to your phone.</p>
                  </div>
                  <label className="block">
                    <span className="block text-sm font-semibold text-slate-700 mb-1.5">Mobile number</span>
                    <div className="flex items-center bg-white border border-slate-200 rounded-2xl overflow-hidden focus-within:border-indigo-400 focus-within:ring-4 focus-within:ring-indigo-100 transition-shadow">
                      <span className="h-14 px-4 flex items-center text-base font-semibold text-slate-600 bg-slate-50 border-r border-slate-200 select-none">
                        +91
                      </span>
                      <input
                        type="tel"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').replace(/^91(?=\d{10})/, '').slice(0, 10))}
                        placeholder="Mobile number"
                        autoFocus
                        inputMode="numeric"
                        autoComplete="tel-national"
                        className="flex-1 min-w-0 h-14 px-4 text-lg font-display font-semibold tracking-wide text-slate-900 placeholder:text-slate-400 placeholder:font-normal placeholder:text-base outline-none bg-transparent tabular-nums"
                      />
                    </div>
                  </label>
                  <Button type="submit" size="lg" loading={loading} disabled={!phoneValid} iconRight={<ArrowRight className="w-5 h-5" />}>
                    Get code
                  </Button>
                </motion.form>
              ) : (
                <motion.div
                  key="otp"
                  initial={{ opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 16 }}
                  className="space-y-5"
                >
                  <div>
                    <h2 className="text-xl font-bold text-slate-900">Enter the code</h2>
                    <p className="text-sm text-slate-500 mt-1">
                      Sent to <span className="font-semibold text-slate-700 tabular-nums">{prettyPhone(phone)}</span>
                      <button
                        type="button"
                        onClick={() => setStep('phone')}
                        className="ml-2 font-semibold text-indigo-600 hover:text-indigo-700"
                      >
                        Change
                      </button>
                    </p>
                  </div>
                  <OtpInput value={otp} onChange={setOtp} onComplete={verify} disabled={loading} error={otpError} />
                  <Button size="lg" loading={loading} disabled={otp.length !== 6} onClick={() => verify(otp)}>
                    Verify and continue
                  </Button>
                  <div className="text-center">
                    {resendIn > 0 ? (
                      <p className="text-sm text-slate-400 tabular-nums h-11 leading-[44px]">Resend code in {resendIn}s</p>
                    ) : (
                      <button
                        type="button"
                        onClick={() => requestOtp()}
                        className="h-11 px-4 text-sm font-semibold text-indigo-600 hover:text-indigo-700"
                      >
                        Resend code
                      </button>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </Card>
          <p className="mt-6 flex items-center justify-center gap-1.5 text-xs text-slate-400 text-center">
            <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
            Photos are hashed and sealed. Nobody can change them later.
          </p>
        </motion.div>
      </div>
    </div>
  )
}
