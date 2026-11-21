import { useState, type FormEvent } from 'react'
import { Eye, EyeOff, LoaderCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)

    const result = await login(email.trim(), password)
    setSubmitting(false)

    if (result.error) {
      setError(result.error)
      return
    }

    navigate('/home', { replace: true })
  }

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="login-title">
        <div className="brand-mark"><span className="brand-icon">D</span><span>Distribonilla</span></div>
        <header className="login-header">
          <h1 id="login-title">Iniciar sesión</h1>
          <p>Accede a tu cuenta para continuar</p>
        </header>

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="field-group">
            <label htmlFor="email">Correo electrónico</label>
            <input id="email" name="email" type="email" autoComplete="email" value={email}
              onChange={(event) => setEmail(event.target.value)} placeholder="nombre@ejemplo.com"
              required disabled={submitting} />
          </div>

          <div className="field-group">
            <label htmlFor="password">Contraseña</label>
            <div className="password-field">
              <input id="password" name="password" type={showPassword ? 'text' : 'password'}
                autoComplete="current-password" value={password}
                onChange={(event) => setPassword(event.target.value)} placeholder="Ingresa tu contraseña"
                required disabled={submitting} />
              <button type="button" className="password-toggle"
                aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                aria-pressed={showPassword} onClick={() => setShowPassword((visible) => !visible)}
                disabled={submitting}>
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          {error && <div className="auth-error" role="alert">{error}</div>}

          <button type="submit" className="primary-button" disabled={submitting}>
            {submitting ? <><LoaderCircle className="spin" size={18} />Iniciando sesión...</> : 'Iniciar sesión'}
          </button>
        </form>
      </section>
    </main>
  )
}
