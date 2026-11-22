export function classifyLoginError(status: unknown, code?: unknown) {
  switch (status) {
    case 401:
      return 'invalid_credentials'
    case 422:
      return 'invalid_request'
    case 429:
      return 'rate_limited'
    case 503:
      return 'unavailable'
    default:
      return status === undefined && code === 'ERR_NETWORK' ? 'network' : 'unexpected'
  }
}

export function getLoginErrorMessage(category: unknown, locale: 'en' | 'es' = 'en'): string {
  const spanish = locale === 'es'
  switch (category) {
    case 'invalid_credentials':
      return spanish ? 'Correo o contraseña incorrectos.' : 'Invalid email or password.'
    case 'invalid_request':
      if (spanish) return 'Revisa el correo y la contraseña.'
      break
    case 'rate_limited':
      return spanish
        ? 'Demasiados intentos. Inténtalo de nuevo más tarde.'
        : 'Too many attempts. Please try again later.'
    case 'network':
      return spanish ? 'No se pudo conectar. Inténtalo de nuevo.' : 'Unable to connect. Please try again.'
    case 'unavailable':
      return spanish ? 'Servicio no disponible. Inténtalo de nuevo.' : 'Service unavailable. Please try again.'
  }

  return spanish ? 'No fue posible iniciar sesión.' : 'Unable to sign in. Please try again.'
}