export type LoginValues = { email: string; password: string }
export type LoginValidationResult = LoginValues & {
  errors: { email?: string; password?: string }
}

type LoginValidationOptions = {
  locale?: 'en' | 'es'
  emailValidity?: { badInput: boolean; typeMismatch: boolean }
}

function hasBasicEmailFormat(email: string): boolean {
  const atIndex = email.indexOf('@')
  if (atIndex <= 0 || atIndex !== email.lastIndexOf('@') || /\s/.test(email)) {
    return false
  }

  const domainDot = email.indexOf('.', atIndex + 2)
  return domainDot !== -1 && domainDot < email.length - 1
}

export function validateLogin(
  input: LoginValues,
  { locale = 'en', emailValidity }: LoginValidationOptions = {},
): LoginValidationResult {
  const email = input.email.trim()
  const errors: LoginValidationResult['errors'] = {}
  const spanish = locale === 'es'

  if (!email) {
    errors.email = spanish ? 'Ingresa tu correo electrónico.' : 'Email is required.'
  } else if (emailValidity?.badInput || emailValidity?.typeMismatch || !hasBasicEmailFormat(email)) {
    errors.email = spanish ? 'Ingresa un correo electrónico válido.' : 'Enter a valid email address.'
  }
  if (!input.password) {
    errors.password = spanish ? 'Ingresa tu contraseña.' : 'Password is required.'
  }
  return { email, password: input.password, errors }
}