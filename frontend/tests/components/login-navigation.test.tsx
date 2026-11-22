import type { Dispatch, SetStateAction } from 'react'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { LoginPage } from '../../src/pages/LoginPage'

const mocks = vi.hoisted(() => ({ login: vi.fn(), navigate: vi.fn(), stateUpdate: vi.fn() }))

vi.mock('react', async (importOriginal) => {
  const react = await importOriginal<typeof import('react')>()
  function useObservedState<T>(initial: T | (() => T)): [T, Dispatch<SetStateAction<T>>] {
    const [value, setValue] = react.useState(initial)
    return [value, (next) => {
      // React can silently discard updates after unmount, so observe the setter call itself.
      mocks.stateUpdate()
      setValue(next)
    }]
  }

  return { ...react, useState: useObservedState }
})

vi.mock('../../src/auth/useAuth', () => ({ useAuth: () => ({ login: mocks.login }) }))
vi.mock('react-router-dom', () => ({ useNavigate: () => mocks.navigate }))

beforeEach(() => vi.resetAllMocks())
afterEach(cleanup)

function submit() {
  const page = render(<LoginPage />)
  fireEvent.change(screen.getByLabelText('Correo electrónico'), { target: { value: 'user@example.com' } })
  fireEvent.change(screen.getByLabelText('Contraseña', { selector: 'input' }), { target: { value: 'fixture' } })
  fireEvent.click(screen.getByRole('button', { name: 'Iniciar sesión' }))
  return page
}

it('handles a rejected navigation promise and restores the form safely', async () => {
  mocks.login.mockResolvedValue({ error: null })
  mocks.navigate.mockRejectedValue(new Error('INTERNAL_FIXTURE_NAVIGATION'))
  submit()

  expect((await screen.findByRole('alert')).textContent).toBe('No fue posible iniciar sesión.')
  expect(mocks.navigate).toHaveBeenCalledExactlyOnceWith('/home', { replace: true })
  expect((screen.getByRole('button', { name: 'Iniciar sesión' }) as HTMLButtonElement).disabled).toBe(false)
  expect(document.body.textContent).not.toContain('INTERNAL_FIXTURE_NAVIGATION')
})

it('restores submission controls after an unexpected rejected login callback', async () => {
  mocks.login.mockRejectedValue(new Error('INTERNAL_FIXTURE_LOGIN'))
  submit()

  expect((await screen.findByRole('alert')).textContent).toBe('No fue posible iniciar sesión.')
  expect(mocks.navigate).not.toHaveBeenCalled()
  expect((screen.getByRole('button', { name: 'Iniciar sesión' }) as HTMLButtonElement).disabled).toBe(false)
})

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: Error) => void
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail })
  return { promise, resolve, reject }
}

it.each(['resolve', 'reject'] as const)('ignores a login %s after the form unmounts', async (outcome) => {
  const login = deferred<{ error: null }>()
  mocks.login.mockReturnValue(login.promise)
  const page = submit()

  page.unmount()
  mocks.stateUpdate.mockClear()
  await act(async () => {
    if (outcome === 'resolve') login.resolve({ error: null })
    else login.reject(new Error('INTERNAL_FIXTURE_UNMOUNTED_LOGIN'))
  })

  expect(mocks.navigate).not.toHaveBeenCalled()
  expect(mocks.stateUpdate).not.toHaveBeenCalled()
})

it.each(['resolve', 'reject'] as const)('ignores a navigation %s after the form unmounts', async (outcome) => {
  const navigation = deferred<void>()
  mocks.login.mockResolvedValue({ error: null })
  mocks.navigate.mockReturnValue(navigation.promise)
  const page = submit()
  await waitFor(() => expect(mocks.navigate).toHaveBeenCalledExactlyOnceWith('/home', { replace: true }))

  page.unmount()
  mocks.stateUpdate.mockClear()
  await act(async () => {
    if (outcome === 'resolve') navigation.resolve()
    else navigation.reject(new Error('INTERNAL_FIXTURE_UNMOUNTED_NAVIGATION'))
  })

  expect(mocks.navigate).toHaveBeenCalledTimes(1)
  expect(mocks.stateUpdate).not.toHaveBeenCalled()
})
