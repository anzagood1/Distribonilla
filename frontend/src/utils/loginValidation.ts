export type LoginValues = { email: string; password: string }
export type LoginValidationResult = LoginValues & {
  errors: { email?: string; password?: string }
}

function hasBasicEmailFormat(email: string): boolean {
  const atIndex = email.indexOf('@')
  if (atIndex <= 0 || atIndex !== email.lastIndexOf('@') || /\s/.test(email)) {
    return false
  }

  const domainDot = email.indexOf('.', atIndex + 2)
  return domainDot !== -1 && domainDot < email.length - 1
}

export function validateLogin(input: LoginValues): LoginValidationResult {
  const email = input.email.trim()
  const errors: LoginValidationResult['errors'] = {}
  if (!email) {
    errors.email = 'Email is required.'
  } else if (!hasBasicEmailFormat(email)) {
    errors.email = 'Enter a valid email address.'
  }
  if (!input.password) errors.password = 'Password is required.'
  return { email, password: input.password, errors }
}
