import { useAuth } from '../auth/useAuth'
import { UserMenu } from '../components/UserMenu'

export function HomePage() {
  const { user } = useAuth()

  return (
    <main className="home-page">
      <header className="home-header">
        <div className="home-brand"><span className="brand-icon">D</span><span>Distribonilla</span></div>
        <UserMenu />
      </header>
      <section className="welcome-card">
        <h1>¡Bienvenido al sistema!</h1>
        <p>Has iniciado sesión correctamente</p>
        {user?.email && <div className="authenticated-email"><span>Sesión iniciada como</span><strong>{user.email}</strong></div>}
      </section>
    </main>
  )
}
