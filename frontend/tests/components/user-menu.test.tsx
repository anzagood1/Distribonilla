import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { UserMenu } from '../../src/components/UserMenu'

const mocks = vi.hoisted(() => ({ logout: vi.fn(), navigate: vi.fn() }))

vi.mock('../../src/auth/useAuth', () => ({
  useAuth: () => ({
    user: { email: 'user@example.com', user_metadata: { name: 'User' } },
    logout: mocks.logout,
  }),
}))
vi.mock('react-router-dom', () => ({ useNavigate: () => mocks.navigate }))

beforeEach(() => vi.resetAllMocks())
afterEach(cleanup)

it('awaits logout navigation', async () => {
  let finishNavigation!: () => void
  mocks.logout.mockResolvedValue({ error: null })
  mocks.navigate.mockReturnValue(new Promise<void>((resolve) => { finishNavigation = resolve }))

  render(<UserMenu />)
  fireEvent.click(screen.getByRole('button', { name: 'Abrir menú de usuario' }))
  fireEvent.click(screen.getByRole('menuitem', { name: 'Cerrar sesión' }))

  await waitFor(() => expect(mocks.navigate).toHaveBeenCalledWith('/login', { replace: true }))
  finishNavigation()
})
