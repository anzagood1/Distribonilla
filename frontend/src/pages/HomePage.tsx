import { useNavigate } from 'react-router-dom'
import { Boxes, PackagePlus, PackageSearch } from 'lucide-react'
import { useAuth } from '../auth/useAuth'
import { UserMenu } from '../components/UserMenu'

export function HomePage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  return (
    <main className="home-page">
      <header className="home-header">
        <div className="home-brand"><span className="brand-icon">D</span><span>Distribonilla</span></div>
        <div className="home-header-actions">
          <nav className="home-nav" aria-label="Navegación principal">
            <button type="button" onClick={() => void navigate('/productos')}>
              Productos
            </button>
            <button type="button" onClick={() => void navigate('/productos/nuevo')}>
              Nuevo producto
            </button>
          </nav>
          <UserMenu />
        </div>
      </header>
      <section className="welcome-card home-dashboard">
        <div className="dashboard-heading">
          <span className="eyebrow">Panel principal</span>
          <h1>¡Bienvenido al sistema!</h1>
          <p>Selecciona una opción para administrar el inventario.</p>
        </div>

        {user?.email && (
          <div className="authenticated-email">
            <span>Sesión iniciada como</span>
            <strong>{user.email}</strong>
          </div>
        )}

        <div className="home-action-grid">
          <button type="button" className="home-action-card" onClick={() => void navigate('/productos')}>
            <span className="home-action-icon"><Boxes size={24} /></span>
            <span>
              <strong>Ver productos</strong>
              <small>Consulta el catálogo y abre el Kardex</small>
            </span>
            <PackageSearch size={18} />
          </button>

          <button type="button" className="home-action-card" onClick={() => void navigate('/productos/nuevo')}>
            <span className="home-action-icon home-action-icon-accent"><PackagePlus size={24} /></span>
            <span>
              <strong>Agregar producto</strong>
              <small>Registra un nuevo producto en el inventario</small>
            </span>
            <PackagePlus size={18} />
          </button>
        </div>
      </section>
    </main>
  )
}
