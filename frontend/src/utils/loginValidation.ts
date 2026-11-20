export type LoginValues = { email: string; password: string }
export type LoginValidationResult = LoginValues & {
  errors: { email?: string; password?: string }
}

export function validateLogin(input: LoginValues): LoginValidationResult {
  const email = input.email.trim()
  const errors: LoginValidationResult['errors'] = {}
  if (!email) {
    errors.email = 'Email is required.'
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.email = 'Enter a valid email address.'
  }
  if (!input.password) errors.password = 'Password is required.'
  return { email, password: input.password, errors }
}
