import assert from 'node:assert/strict'
import test from 'node:test'
import { validateLogin } from '../src/utils/loginValidation.ts'

test('requires an email address', () => {
  const result = validateLogin({ email: '', password: 'example-password' })
  assert.equal(result.errors.email, 'Email is required.')
})

test('treats whitespace-only email as empty', () => {
  const result = validateLogin({ email: '  \t ', password: 'example-password' })
  assert.equal(result.errors.email, 'Email is required.')
  assert.equal(result.email, '')
})

test('rejects malformed email addresses', () => {
  for (const email of ['user', 'user@', '@example.com', 'user@example', 'a b@example.com']) {
    const result = validateLogin({ email, password: 'example-password' })
    assert.equal(result.errors.email, 'Enter a valid email address.')
  }
})

test('requires a nonempty password', () => {
  const result = validateLogin({ email: 'user@example.com', password: '' })
  assert.equal(result.errors.password, 'Password is required.')
})

test('reports both missing fields', () => {
  const result = validateLogin({ email: '', password: '' })
  assert.deepEqual(result.errors, {
    email: 'Email is required.',
    password: 'Password is required.',
  })
})

test('trims the email and preserves the password exactly', () => {
  const result = validateLogin({ email: '  User@example.com  ', password: '  p@ss  ' })
  assert.equal(result.email, 'User@example.com')
  assert.equal(result.password, '  p@ss  ')
  assert.deepEqual(result.errors, {})
})

test('does not impose registration rules on an existing password', () => {
  for (const password of ['x', '   ']) {
    const result = validateLogin({ email: 'user@example.com', password })
    assert.equal(result.password, password)
    assert.deepEqual(result.errors, {})
  }
})
