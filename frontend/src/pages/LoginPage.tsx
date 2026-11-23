import { useLayoutEffect, useRef, useState, type SubmitEvent } from 'react'
import { Eye, EyeOff, LoaderCircle } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { getLoginErrorMessage } from '../utils/loginErrors'
import { validateLogin, type LoginValidationResult } from '../utils/loginValidation'

export function LoginPage() {
  const { login, configurationError } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<LoginValidationResult['errors']>({})
  const mounted = useRef(false)

  useLayoutEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  const handleSubmit = async (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)

    const emailInput = event.currentTarget.elements.namedItem('email')
    const validated = validateLogin({ email, password }, {
      locale: 'es',
      emailValidity: emailInput instanceof HTMLInputElement ? emailInput.validity : undefined,
    })
    setFieldErrors(validated.errors)
    if (validated.errors.email || validated.errors.password) return

    setSubmitting(true)
    try {
      const result = await login(validated.email, validated.password)
      if (!mounted.current) return

      if (result.error) {
        setError(result.error)
        return
      }

      await navigate('/home', { replace: true })
    } catch {
      if (mounted.current) setError(getLoginErrorMessage('unexpected', 'es'))
    } finally {
      if (mounted.current) setSubmitting(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="login-title">
        <div className="brand-mark"><span className="brand-icon">D</span><span>Distribonilla</span></div>
        <header className="login-header">
          <h1 id="login-title">Iniciar sesión</h1>
          <p>Accede a tu cuenta para continuar</p>
        </header>

        <form className="login-form" onSubmit={handleSubmit} noValidate>
          {configurationError && (
            <div className="auth-error" role="alert">{configurationError}</div>
          )}

          <div className="field-group">
            <label htmlFor="email">Correo electrónico</label>
            <input id="email" name="email" type="email" autoComplete="email" value={email}
              onChange={(event) => {
                setEmail(event.target.value)
                setFieldErrors((current) => ({ ...current, email: undefined }))
                setError(null)
              }}
              placeholder="nombre@ejemplo.com" required disabled={submitting}
              aria-invalid={Boolean(fieldErrors.email)}
              aria-describedby={fieldErrors.email ? 'login-email-error' : undefined} />
            {fieldErrors.email && (
              <div className="auth-error" id="login-email-error" role="alert">{fieldErrors.email}</div>
            )}
          </div>

          <div className="field-group">
            <label htmlFor="password">Contraseña</label>
            <div className="password-field">
              <input id="password" name="password" type={showPassword ? 'text' : 'password'}
                autoComplete="current-password" value={password}
                onChange={(event) => {
                  setPassword(event.target.value)
                  setFieldErrors((current) => ({ ...current, password: undefined }))
                  setError(null)
                }}
                placeholder="Ingresa tu contraseña" required disabled={submitting}
                aria-invalid={Boolean(fieldErrors.password)}
                aria-describedby={fieldErrors.password ? 'login-password-error' : undefined} />
              <button type="button" className="password-toggle"
                aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                aria-pressed={showPassword} onClick={() => setShowPassword((visible) => !visible)}
                disabled={submitting}>
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
            {fieldErrors.password && (
              <div className="auth-error" id="login-password-error" role="alert">{fieldErrors.password}</div>
            )}
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
