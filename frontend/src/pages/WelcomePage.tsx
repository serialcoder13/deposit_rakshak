import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Sparkles } from 'lucide-react'
import { toast } from 'sonner'
import { useQueryClient } from '@tanstack/react-query'
import { api, errorMessage } from '../api'
import { Button, Card, Field } from '../components/ui'
import { useMe } from '../lib/hooks'
import { prettyPhone } from '../lib/format'

/** First-time name step after sign up. */
export default function WelcomePage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data: me } = useMe()
  const [name, setName] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (me?.name) setName((n) => n || me.name)
  }, [me?.name])

  async function save(e: React.FormEvent) {
    e.preventDefault()
    const clean = name.trim()
    if (clean.length < 2) {
      toast.error('Please enter your name')
      return
    }
    setSaving(true)
    try {
      const updated = await api.updateMe(clean)
      qc.setQueryData(['me'], updated)
      navigate('/', { replace: true })
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-dvh flex flex-col pt-safe">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex-1 max-w-md w-full mx-auto px-4 pt-16 pb-safe-8"
      >
        <div className="w-16 h-16 rounded-3xl bg-brand-gradient flex items-center justify-center shadow-soft-lg">
          <Sparkles className="w-8 h-8 text-white" />
        </div>
        <h1 className="mt-6 text-3xl font-extrabold text-slate-900 tracking-tight">What should we call you?</h1>
        <p className="mt-2 text-slate-500">
          Your owner or tenant will see this name on the shared record.
          {me?.phone && <span className="block mt-1 tabular-nums">Signed in as {prettyPhone(me.phone)}</span>}
        </p>
        <Card className="mt-8">
          <form onSubmit={save} className="space-y-5">
            <Field
              label="Your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Full name"
              autoFocus
              autoComplete="name"
              maxLength={60}
            />
            <Button type="submit" size="lg" loading={saving} disabled={name.trim().length < 2} iconRight={<ArrowRight className="w-5 h-5" />}>
              Continue
            </Button>
          </form>
        </Card>
      </motion.div>
    </div>
  )
}
