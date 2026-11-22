import { useEffect, useRef, useState } from 'react'
import { LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

export function UserMenu() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [signingOut, setSigningOut] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const closeMenu = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', closeMenu)
    return () => document.removeEventListener('mousedown', closeMenu)
  }, [])

  if (!user) return null

  let name: string | null = null
  if (typeof user.user_metadata?.full_name === 'string') {
    name = user.user_metadata.full_name
  } else if (typeof user.user_metadata?.name === 'string') {
    name = user.user_metadata.name
  }
  const email = user.email ?? ''
  const initial = (name || email).trim().charAt(0).toUpperCase() || 'U'

  const handleLogout = async () => {
    setSigningOut(true)
    await logout()
    setSigningOut(false)
    setOpen(false)
    await navigate('/login', { replace: true })
  }

  return (
    <div className="user-menu" ref={menuRef}>
      <button type="button" className="avatar-button" aria-label="Abrir menú de usuario"
        aria-expanded={open} onClick={() => setOpen((value) => !value)}>{initial}</button>
      {open && (
        <div className="user-popover" role="menu">
          <div className="user-details">
            <div className="popover-avatar" aria-hidden="true">{initial}</div>
            <div className="user-text">{name && <strong>{name}</strong>}<span>{email}</span></div>
          </div>
          <button type="button" className="logout-button" role="menuitem"
            onClick={handleLogout} disabled={signingOut}>
            <LogOut size={18} />{signingOut ? 'Cerrando sesión...' : 'Cerrar sesión'}
          </button>
        </div>
      )}
    </div>
  )
}
