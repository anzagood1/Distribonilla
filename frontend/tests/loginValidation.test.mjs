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

test('preserves acceptance of domains with multiple dots', () => {
  for (const email of [
    'user@sub.example.com',
    'user@example..com',
    'user@.example.com',
    'user@example.com.',
  ]) {
    assert.deepEqual(validateLogin({ email, password: 'example-password' }).errors, {}, email)
  }
})

test('rejects extra at signs, internal whitespace, and misplaced domain dots', () => {
  for (const email of [
    'user@@example.com',
    'user@example.com@other.com',
    'user@exam ple.com',
    'user@example.\tcom',
    'us\u00a0er@example.com',
    'user@.example',
    'user@example.',
    'user@.',
  ]) {
    const result = validateLogin({ email, password: 'example-password' })
    assert.equal(result.errors.email, 'Enter a valid email address.', email)
  }
})

test('validates long domains without changing the password', () => {
  const label = 'x'.repeat(4096)
  const password = ' \tp@ss\u00e9 \n'
  const valid = validateLogin({ email: `user@sub.${label}.example.com`, password })
  const invalid = validateLogin({ email: `user@${label}.`, password })

  assert.deepEqual(valid.errors, {})
  assert.equal(invalid.errors.email, 'Enter a valid email address.')
  assert.equal(valid.password, password)
  assert.equal(invalid.password, password)
})
