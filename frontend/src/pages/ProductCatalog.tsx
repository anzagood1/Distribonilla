import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  ArrowUpRight,
  Boxes,
  History,
  PackagePlus,
  Home,
  RefreshCw,
  Search,
  X,
} from 'lucide-react';
import { getProducts } from '../services/productService';
import type { Product } from '../types/product';

function ProductCatalog() {
  const navigate = useNavigate();
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const loadProducts = async () => {
      try {
        setLoading(true);
        setError('');

        const data = await getProducts();
        setProducts(data);
      } catch (err: unknown) {
        console.error('Error al cargar los productos:', err);
        setError('No se pudieron cargar los productos.');
      } finally {
        setLoading(false);
      }
    };

    void loadProducts();
  }, [reloadKey]);

  const filteredProducts = useMemo(() => {
    const searchValue = search.trim().toLowerCase();

    if (!searchValue) {
      return products;
    }

    return products.filter((product) => {
      const matchesId = String(product.id).includes(searchValue);
      const matchesName = product.nombre.toLowerCase().includes(searchValue);

      return matchesId || matchesName;
    });
  }, [products, search]);

  const renderCatalog = () => {
    if (loading) {
      return (
        <div className="catalog-loading" aria-label="Cargando productos">
          {[0, 1, 2, 3].map((item) => (
            <div className="product-skeleton" key={item}>
              <div className="skeleton-block skeleton-icon" />
              <div className="skeleton-lines">
                <div className="skeleton-block skeleton-title" />
                <div className="skeleton-block skeleton-subtitle" />
              </div>
            </div>
          ))}
        </div>
      );
    }

    if (error) {
      return (
        <div className="catalog-error" role="alert">
          <div className="error-icon"><AlertCircle size={22} /></div>
          <div>
            <strong>{error}</strong>
            <p>Comprueba la conexión con el servidor e inténtalo de nuevo.</p>
          </div>
          <button
            type="button"
            className="secondary-button"
            onClick={() => setReloadKey((value) => value + 1)}
          >
            <RefreshCw size={16} />
            Reintentar
          </button>
        </div>
      );
    }

    if (filteredProducts.length === 0) {
      return (
        <div className="empty-state">
          <div className="empty-icon"><Boxes size={28} /></div>
          <h3>{search ? 'Sin coincidencias' : 'Todavía no hay productos'}</h3>
          <p>
            {search
              ? `No encontramos productos para "${search}".`
              : 'Registra el primer producto para comenzar.'}
          </p>
          {search ? (
            <button type="button" className="secondary-button" onClick={() => setSearch('')}>
              <X size={16} /> Limpiar búsqueda
            </button>
          ) : (
            <button
              type="button"
              className="primary-button"
              onClick={() => void navigate('/productos/nuevo')}
            >
              <PackagePlus size={17} /> Crear producto
            </button>
          )}
        </div>
      );
    }

    return (
      <div className="table-container">
        <table className="products-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Producto</th>
              <th>Descripción</th>
              <th>Talla</th>
              <th>Precio</th>
              <th>Stock actual</th>
              <th>Stock mínimo</th>
              <th>Kardex</th>
            </tr>
          </thead>

          <tbody>
            {filteredProducts.map((product) => (
              <tr key={product.id} tabIndex={0}>
                <td><span className="product-id">#{product.id}</span></td>
                <td>
                  <div className="product-cell">
                    <span className="product-avatar">{product.nombre.charAt(0).toUpperCase()}</span>
                    <div>
                      <span className="product-name">{product.nombre}</span>
                      <span className="product-code">Código {product.id.toString().padStart(5, '0')}</span>
                    </div>
                  </div>
                </td>
                <td>{product.descripcion || '—'}</td>
                <td>{product.talla ? <span className="size-badge">{product.talla}</span> : '—'}</td>
                <td><strong className="price">${Number(product.precio_unitario).toFixed(2)}</strong></td>
                <td>
                  <span className={`stock-badge ${product.stock_actual <= product.stock_minimo ? 'stock-low' : 'stock-ok'}`}>
                    {product.stock_actual} unidades
                  </span>
                </td>
                <td>{product.stock_minimo}</td>
                <td>
                  <button
                    type="button"
                    className="kardex-button"
                    onClick={() => void navigate(`/productos/${product.id}/kardex`)}
                    aria-label={`Abrir kardex de ${product.nombre}`}
                  >
                    <History size={15} />
                    Ver historial
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <main className="products-page">
      <header className="catalog-header">
        <div className="catalog-brand">
          <span className="catalog-brand-mark">D</span>
          <div>
            <span className="brand-name">Distribonilla</span>
            <span className="brand-section">Gestión de inventario</span>
          </div>
        </div>
        <nav className="catalog-nav" aria-label="Navegación principal">
          <button type="button" onClick={() => void navigate('/home')}>
            <Home size={16} /> Inicio
          </button>
          <button type="button" onClick={() => void navigate('/productos/nuevo')}>
            <PackagePlus size={16} /> Nuevo producto
          </button>
        </nav>
      </header>

      <div className="catalog-content">
        <section className="catalog-heading">
          <div>
            <span className="eyebrow">Catálogo</span>
            <h1>Productos</h1>
            <p>Consulta, busca y administra tu inventario.</p>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Actualizar catálogo"
            onClick={() => setReloadKey((value) => value + 1)}
          >
            <RefreshCw size={18} />
          </button>
        </section>

        <section className="metrics-grid" aria-label="Resumen del inventario">
          <article className="metric-card metric-primary">
            <span className="metric-icon"><Boxes size={20} /></span>
            <div>
              <span>Total de productos</span>
              <strong>{loading ? '—' : products.length}</strong>
            </div>
            <ArrowUpRight className="metric-arrow" size={18} />
          </article>
          <article className="metric-card">
            <span className="metric-icon metric-success"><Boxes size={20} /></span>
            <div>
              <span>Existencias</span>
              <strong>{loading ? '—' : products.reduce((sum, product) => sum + product.stock_actual, 0)}</strong>
            </div>
          </article>
          <article className="metric-card">
            <span className="metric-icon metric-warning"><AlertCircle size={20} /></span>
            <div>
              <span>Stock bajo</span>
              <strong>{loading ? '—' : products.filter((product) => product.stock_actual <= product.stock_minimo).length}</strong>
            </div>
          </article>
        </section>

        <section className="catalog-card">
          <div className="catalog-toolbar">
            <div>
              <h2>Inventario</h2>
              <p>{filteredProducts.length} {filteredProducts.length === 1 ? 'producto encontrado' : 'productos encontrados'}</p>
            </div>
            <div className="search-container">
              <Search size={18} />
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Buscar por ID o producto"
                aria-label="Buscar productos por ID o nombre"
              />
              {search && (
                <button type="button" className="clear-search" aria-label="Limpiar búsqueda" onClick={() => setSearch('')}>
                  <X size={16} />
                </button>
              )}
            </div>
          </div>
          {renderCatalog()}
        </section>
      </div>
    </main>
  );
}

export default ProductCatalog;