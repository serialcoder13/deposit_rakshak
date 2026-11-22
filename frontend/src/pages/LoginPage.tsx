/**
 * LoginPage.tsx — Screen 1 (SPEC §11)
 * Phone number + OTP entry. Demo hint shown inline.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setToken } from '../api'

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
    <div style={{ maxWidth: 400, margin: '80px auto', padding: '0 24px', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Deposit Rakshak</h1>
      <p style={{ color: '#57606a', marginBottom: 32 }}>Tamper-evident rental deposit tracker</p>

      {step === 'phone' ? (
        <form onSubmit={handleRequestOtp}>
          <label style={{ display: 'block', marginBottom: 4, fontWeight: 600 }}>Phone number</label>
          <input
            type="tel"
            value={phone}
            onChange={e => setPhone(e.target.value)}
            placeholder="9999990001"
            required
            style={{ width: '100%', padding: '12px 16px', fontSize: 18, borderRadius: 8, border: '1px solid #e5e7eb', boxSizing: 'border-box' }}
          />
          <button
            type="submit"
            disabled={loading}
            style={{ marginTop: 16, width: '100%', padding: '14px', fontSize: 18, background: '#1e40af', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}
          >
            {loading ? 'Sending…' : 'Send OTP'}
          </button>
        </form>
      ) : (
        <form onSubmit={handleVerifyOtp}>
          <p style={{ background: '#f0fdf4', border: '1px solid #86efac', borderRadius: 8, padding: '12px 16px', marginBottom: 16 }}>
            Demo OTP: <strong>123456</strong>
          </p>
          <label style={{ display: 'block', marginBottom: 4, fontWeight: 600 }}>Enter OTP</label>
          <input
            type="text"
            value={otp}
            onChange={e => setOtp(e.target.value)}
            placeholder="123456"
            maxLength={6}
            required
            style={{ width: '100%', padding: '12px 16px', fontSize: 24, letterSpacing: 8, borderRadius: 8, border: '1px solid #e5e7eb', boxSizing: 'border-box' }}
          />
          <button
            type="submit"
            disabled={loading}
            style={{ marginTop: 16, width: '100%', padding: '14px', fontSize: 18, background: '#1e40af', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' }}
          >
            {loading ? 'Verifying…' : 'Verify'}
          </button>
          <button type="button" onClick={() => setStep('phone')} style={{ marginTop: 8, width: '100%', padding: '12px', background: 'none', border: '1px solid #e5e7eb', borderRadius: 8, cursor: 'pointer' }}>
            Back
          </button>
        </form>
      )}

      {error && <p style={{ color: '#dc2626', marginTop: 12 }}>{error}</p>}
    </div>
  )
}
