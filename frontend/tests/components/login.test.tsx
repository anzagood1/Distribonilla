import type { AuthChangeEvent, Session } from '@supabase/supabase-js'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { AxiosError } from 'axios'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from '../../src/App'

const mocks = vi.hoisted(() => ({
  getSession: vi.fn(),
  onAuthStateChange: vi.fn(),
  unsubscribe: vi.fn(),
  setSession: vi.fn(),
  signOut: vi.fn(),
  loginWithBackend: vi.fn(),
}))

vi.mock('../../src/utils/supabase', () => ({ supabase: { auth: mocks } }))
vi.mock('../../src/services/auth', () => ({ loginWithBackend: mocks.loginWithBackend }))

const wireTokens = { access_token: 'fixture-access', refresh_token: 'fixture-refresh' }
const loginResponse = { ...wireTokens, token_type: 'bearer', expires_in: 3600 }
const session = {
  ...loginResponse,
  user: { id: 'fixture-user', email: 'User@example.com' },
} as Session
const internal = 'INTERNAL_FIXTURE_DETAIL'
const fallback = 'No fue posible iniciar sesión.'
const invalidEmail = 'Ingresa un correo electrónico válido.'
let onAuthChange: ((event: AuthChangeEvent, value: Session | null) => void) | undefined

beforeEach(() => {
  vi.resetAllMocks()
  onAuthChange = undefined
  mocks.getSession.mockResolvedValue({ data: { session: null }, error: null })
  mocks.onAuthStateChange.mockImplementation((callback: typeof onAuthChange) => {
    onAuthChange = callback
    return { data: { subscription: { unsubscribe: mocks.unsubscribe } } }
  })
  mocks.setSession.mockImplementation(async () => {
    onAuthChange?.('SIGNED_IN', session)
    return { error: null }
  })
  mocks.signOut.mockImplementation(async () => {
    onAuthChange?.('SIGNED_OUT', null)
    return { error: null }
  })
})

afterEach(cleanup)

function renderApp(path = '/login') {
  return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>)
}

async function openLogin() {
  renderApp()
  return await screen.findByRole('button', { name: 'Iniciar sesión' })
}

function fill(email: string, password: string) {
  fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: email } })
  fireEvent.change(screen.getByLabelText('Contraseña', { selector: 'input' }), { target: { value: password } })
}

async function submit() {
  const button = await openLogin()
  fill('  User@example.com  ', '  fixture password  ')
  fireEvent.click(button)
}

async function expectSafeError(message: string) {
  expect((await screen.findByRole('alert')).textContent).toBe(message)
  expect(document.body.textContent).not.toContain(internal)
  expect(document.body.textContent).not.toContain(wireTokens.access_token)
  expect(document.body.textContent).not.toContain(wireTokens.refresh_token)
  expect(screen.queryByRole('heading', { name: /bienvenido/i })).toBeNull()
  expect((screen.getByRole('button', { name: 'Iniciar sesión' }) as HTMLButtonElement).disabled).toBe(false)
}

it('shows accessible field errors for blanks and clears only the edited field', async () => {
  const button = await openLogin()
  const email = screen.getByLabelText('Correo electrónico')
  const password = screen.getByLabelText('Contraseña', { selector: 'input' })

  fireEvent.click(button)
  expect(screen.getByText('Ingresa tu correo electrónico.').id).toBe('login-email-error')
  expect(screen.getByText('Ingresa tu contraseña.').id).toBe('login-password-error')
  expect(email.getAttribute('aria-invalid')).toBe('true')
  expect(email.getAttribute('aria-describedby')).toBe('login-email-error')
  expect(password.getAttribute('aria-invalid')).toBe('true')
  expect(password.getAttribute('aria-describedby')).toBe('login-password-error')

  fireEvent.change(email, { target: { value: 'user@example.com' } })
  expect(screen.queryByText('Ingresa tu correo electrónico.')).toBeNull()
  expect(screen.getByText('Ingresa tu contraseña.')).toBeTruthy()
  expect(mocks.loginWithBackend).not.toHaveBeenCalled()
})

it.each([
  ['user@example..com', true],
  ['user@intranet', false],
])('rejects %s before invoking the backend', async (email, nativeMismatch) => {
  const button = await openLogin()
  fill(email, 'fixture')
  const input = screen.getByLabelText<HTMLInputElement>('Correo electrónico')
  expect(input.type).toBe('email')
  expect(input.validity.typeMismatch).toBe(nativeMismatch)
  fireEvent.click(button)
  expect(screen.getByRole('alert').textContent).toBe(invalidEmail)
  expect(mocks.loginWithBackend).not.toHaveBeenCalled()
})

it('never submits a blank password', async () => {
  const button = await openLogin()
  fill('user@example.com', '')
  fireEvent.click(button)
  expect(screen.getByRole('alert').textContent).toBe('Ingresa tu contraseña.')
  expect(mocks.loginWithBackend).not.toHaveBeenCalled()
})

it.each([
  [401, 'Correo o contraseña incorrectos.'],
  [422, 'Revisa el correo y la contraseña.'],
  [429, 'Demasiados intentos. Inténtalo de nuevo más tarde.'],
  [503, 'Servicio no disponible. Inténtalo de nuevo.'],
  [500, fallback],
])('shows a fixed safe message for HTTP %i', async (status, message) => {
  const error = Object.assign(new AxiosError(internal), {
    response: { status, data: { detail: internal } },
  })
  mocks.loginWithBackend.mockRejectedValue(error)
  await submit()
  await expectSafeError(message)
  expect(mocks.setSession).not.toHaveBeenCalled()
})

it('shows a safe message for a network error', async () => {
  mocks.loginWithBackend.mockRejectedValue(new AxiosError(internal, 'ERR_NETWORK'))
  await submit()
  await expectSafeError('No se pudo conectar. Inténtalo de nuevo.')
  expect(mocks.setSession).not.toHaveBeenCalled()
})

it('handles an unexpected rejection without exposing it', async () => {
  mocks.loginWithBackend.mockRejectedValue(new Error(internal))
  await submit()
  await expectSafeError(fallback)
  expect(mocks.setSession).not.toHaveBeenCalled()
})

it.each([
  { ...loginResponse, access_token: 42 },
  { ...loginResponse, access_token: '' },
  { ...loginResponse, refresh_token: null },
  { ...loginResponse, refresh_token: '' },
])('rejects a malformed success response before establishing a session', async (response) => {
  mocks.loginWithBackend.mockResolvedValue(response)
  await submit()
  await expectSafeError(fallback)
  expect(mocks.setSession).not.toHaveBeenCalled()
})

it.each(['returned', 'thrown'])('safely handles a %s setSession error', async (kind) => {
  mocks.loginWithBackend.mockResolvedValue(loginResponse)
  if (kind === 'returned') mocks.setSession.mockResolvedValue({ error: { message: internal } })
  else mocks.setSession.mockRejectedValue(new Error(internal))

  await submit()
  await expectSafeError(fallback)
  expect(mocks.setSession).toHaveBeenCalledWith(wireTokens)
})

it('recovers from rejected getSession, unblocks loading and protects home', async () => {
  mocks.getSession.mockRejectedValue(new Error(internal))
  const page = renderApp('/home')
  expect(screen.getByRole('status')).toBeTruthy()

  expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeTruthy()
  expect(screen.queryByRole('status')).toBeNull()
  expect(screen.queryByRole('heading', { name: /bienvenido/i })).toBeNull()
  expect(mocks.loginWithBackend).not.toHaveBeenCalled()
  page.unmount()
  expect(mocks.unsubscribe).toHaveBeenCalledTimes(1)
})

it('does not discard an auth-event session if initial getSession rejects later', async () => {
  let rejectSession: (reason: Error) => void = () => {}
  mocks.getSession.mockReturnValue(new Promise((_, reject) => { rejectSession = reject }))
  renderApp('/home')
  expect(screen.getByRole('status')).toBeTruthy()

  await act(async () => onAuthChange?.('SIGNED_IN', session))
  expect(await screen.findByRole('heading', { name: /bienvenido/i })).toBeTruthy()
  await act(async () => rejectSession(new Error(internal)))
  expect(screen.getByRole('heading', { name: /bienvenido/i })).toBeTruthy()
})

it('ignores a rejected session read after unmount and unsubscribes', async () => {
  let rejectSession: (reason: Error) => void = () => {}
  mocks.getSession.mockReturnValue(new Promise((_, reject) => { rejectSession = reject }))
  const page = renderApp('/home')
  page.unmount()

  await act(async () => rejectSession(new Error(internal)))
  expect(mocks.unsubscribe).toHaveBeenCalledTimes(1)
  expect(screen.queryByRole('status')).toBeNull()
})

it('restores an existing session and keeps the protected route available', async () => {
  mocks.getSession.mockResolvedValue({ data: { session }, error: null })
  renderApp('/home')
  expect(await screen.findByRole('heading', { name: /bienvenido/i })).toBeTruthy()
  expect(mocks.loginWithBackend).not.toHaveBeenCalled()
})

it('logs in with exact credentials, establishes session and signs out', async () => {
  mocks.loginWithBackend.mockResolvedValue(loginResponse)
  await submit()
  expect(await screen.findByRole('heading', { name: /bienvenido/i })).toBeTruthy()
  expect(mocks.loginWithBackend).toHaveBeenCalledExactlyOnceWith('User@example.com', '  fixture password  ')
  expect(mocks.setSession).toHaveBeenCalledExactlyOnceWith(wireTokens)

  fireEvent.click(screen.getByRole('button', { name: 'Abrir menú de usuario' }))
  fireEvent.click(screen.getByRole('menuitem', { name: 'Cerrar sesión' }))
  expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeTruthy()
  await waitFor(() => expect(mocks.signOut).toHaveBeenCalledTimes(1))
})

function deferInitialSession() {
  let finish: (result: { data: { session: Session | null }; error: null }) => void = () => {}
  mocks.getSession.mockReturnValue(new Promise((resolve) => { finish = resolve }))
  return (value: Session | null) => finish({ data: { session: value }, error: null })
}

it('SIGNED_IN takes precedence over a late empty initial read', async () => {
  const finishInitialSession = deferInitialSession()
  renderApp('/home')

  await act(async () => onAuthChange?.('SIGNED_IN', session))
  expect(await screen.findByRole('heading', { name: /bienvenido/i })).toBeTruthy()

  await act(async () => finishInitialSession(null))
  expect(screen.getByRole('heading', { name: /bienvenido/i })).toBeTruthy()
  expect(screen.queryByRole('heading', { name: 'Iniciar sesión' })).toBeNull()
})

it('SIGNED_OUT takes precedence over a late initial read with the old session', async () => {
  const finishInitialSession = deferInitialSession()
  renderApp('/home')

  await act(async () => onAuthChange?.('SIGNED_IN', session))
  await screen.findByRole('heading', { name: /bienvenido/i })
  fireEvent.click(screen.getByRole('button', { name: 'Abrir menú de usuario' }))
  fireEvent.click(screen.getByRole('menuitem', { name: 'Cerrar sesión' }))
  expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeTruthy()

  await act(async () => finishInitialSession(session))
  expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeTruthy()
  expect(screen.queryByRole('heading', { name: /bienvenido/i })).toBeNull()
})

it('uses INITIAL_SESSION to finish loading a persisted session', async () => {
  const finishInitialSession = deferInitialSession()
  renderApp('/home')
  expect(screen.getByRole('status')).toBeTruthy()

  await act(async () => onAuthChange?.('INITIAL_SESSION', session))
  expect(await screen.findByRole('heading', { name: /bienvenido/i })).toBeTruthy()
  expect(screen.queryByRole('status')).toBeNull()
  await act(async () => finishInitialSession(null))
  expect(screen.getByRole('heading', { name: /bienvenido/i })).toBeTruthy()
})

it('uses a null INITIAL_SESSION to finish loading a signed-out user', async () => {
  deferInitialSession()
  renderApp('/home')
  expect(screen.getByRole('status')).toBeTruthy()

  await act(async () => onAuthChange?.('INITIAL_SESSION', null))
  expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeTruthy()
  expect(screen.queryByRole('status')).toBeNull()
})

it('does not let an older INITIAL_SESSION supersede a sign-out event', async () => {
  const finishInitialSession = deferInitialSession()
  renderApp('/home')

  await act(async () => onAuthChange?.('SIGNED_OUT', null))
  expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeTruthy()
  await act(async () => onAuthChange?.('INITIAL_SESSION', session))
  await act(async () => finishInitialSession(session))
  expect(screen.getByRole('heading', { name: 'Iniciar sesión' })).toBeTruthy()
  expect(screen.queryByRole('heading', { name: /bienvenido/i })).toBeNull()
})

it('keeps the session from TOKEN_REFRESHED when the older initial read completes', async () => {
  const finishInitialSession = deferInitialSession()
  const refreshed = { ...session, user: { ...session.user, email: 'Refreshed@example.com' } }
  renderApp('/home')

  await act(async () => onAuthChange?.('INITIAL_SESSION', session))
  expect(await screen.findByText('User@example.com')).toBeTruthy()
  await act(async () => onAuthChange?.('TOKEN_REFRESHED', refreshed))
  expect(screen.getByText('Refreshed@example.com')).toBeTruthy()

  await act(async () => finishInitialSession(session))
  expect(screen.getByText('Refreshed@example.com')).toBeTruthy()
  expect(screen.queryByText('User@example.com')).toBeNull()
})
