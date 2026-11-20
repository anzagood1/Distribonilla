export function getLoginErrorMessage(category: unknown): string {
  switch (category) {
    case 'invalid_credentials':
      return 'Invalid email or password.'
    case 'rate_limited':
      return 'Too many attempts. Please try again later.'
    case 'network':
      return 'Unable to connect. Please try again.'
    case 'unavailable':
      return 'Service unavailable. Please try again.'
    default:
      return 'Unable to sign in. Please try again.'
  }
}
