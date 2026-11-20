import assert from 'node:assert/strict'
import test from 'node:test'
import { getLoginErrorMessage } from '../src/utils/loginErrors.ts'

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
