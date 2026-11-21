import assert from 'node:assert/strict'
import test from 'node:test'
import { classifyLoginError, getLoginErrorMessage } from '../src/utils/loginErrors.ts'

test('shows a generic message for invalid credentials', () => {
  assert.equal(getLoginErrorMessage('invalid_credentials'), 'Invalid email or password.')
})

test('distinguishes rate limits, connection failures, and unavailable service', () => {
  assert.equal(getLoginErrorMessage('rate_limited'), 'Too many attempts. Please try again later.')
  assert.equal(getLoginErrorMessage('network'), 'Unable to connect. Please try again.')
  assert.equal(getLoginErrorMessage('unavailable'), 'Service unavailable. Please try again.')
})

test('returns a safe generic message for unknown or malformed categories', () => {
  const safeMessage = 'Unable to sign in. Please try again.'
  for (const input of ['unexpected', 'unknown', null, undefined, 401, new Error('DUMMY_SECRET')]) {
    assert.equal(getLoginErrorMessage(input), safeMessage)
  }
  const response = { message: 'DUMMY_SECRET', detail: 'DUMMY_SECRET' }
  assert.equal(getLoginErrorMessage(response), safeMessage)
  assert.equal(getLoginErrorMessage(response).includes('DUMMY_SECRET'), false)
})

test('classifies the supported HTTP statuses without inspecting response details', () => {
  assert.equal(classifyLoginError(401), 'invalid_credentials')
  assert.equal(classifyLoginError(422), 'invalid_request')
  assert.equal(classifyLoginError(429), 'rate_limited')
  assert.equal(classifyLoginError(503), 'unavailable')
})

test('distinguishes an explicit network failure from unexpected errors', () => {
  assert.equal(classifyLoginError(undefined, 'ERR_NETWORK'), 'network')
  assert.equal(classifyLoginError(undefined), 'unexpected')
  assert.equal(classifyLoginError(500, 'ERR_NETWORK'), 'unexpected')
  assert.equal(classifyLoginError('401'), 'unexpected')
  assert.equal(classifyLoginError({ status: 401, detail: 'DUMMY_SECRET' }), 'unexpected')
})

test('returns fixed Spanish messages for authentication and transport failures', () => {
  const messages = {
    invalid_credentials: 'Correo o contraseña incorrectos.',
    invalid_request: 'Revisa el correo y la contraseña.',
    rate_limited: 'Demasiados intentos. Inténtalo de nuevo más tarde.',
    network: 'No se pudo conectar. Inténtalo de nuevo.',
    unavailable: 'Servicio no disponible. Inténtalo de nuevo.',
    unexpected: 'No fue posible iniciar sesión.',
  }
  for (const [category, message] of Object.entries(messages)) {
    assert.equal(getLoginErrorMessage(category, 'es'), message)
  }
  assert.equal(getLoginErrorMessage({ detail: 'DUMMY_SECRET' }, 'es'), messages.unexpected)
  assert.equal(getLoginErrorMessage('invalid_request'), 'Unable to sign in. Please try again.')
})
