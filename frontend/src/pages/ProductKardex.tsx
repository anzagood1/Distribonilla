import { useEffect, useState, type ReactNode } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Boxes, CalendarDays, Home, RefreshCw, X } from 'lucide-react';
import { getProductMovements, getProducts } from '../services/productService';
import type { InventoryMovement, Product } from '../types/product';

function formatDate(value: string) {
  return new Intl.DateTimeFormat('es-EC', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function ProductKardex() {
  const navigate = useNavigate();
  const { productId } = useParams();
  const [product, setProduct] = useState<Product | null>(null);
  const [movements, setMovements] = useState<InventoryMovement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [filterError, setFilterError] = useState('');

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError('');
        setFilterError('');
        if (fromDate && toDate && fromDate > toDate) {
          setFilterError('La fecha inicial no puede ser posterior a la fecha final.');
          setMovements([]);
          setLoading(false);
          return;
        }
        const id = Number(productId);
        const [products, movementRows] = await Promise.all([
          getProducts(),
          getProductMovements(id, fromDate, toDate),
        ]);
        setProduct(products.find((item) => item.id === id) ?? null);
        setMovements(movementRows);
      } catch (err) {
        console.error('Error al cargar el kardex:', err);
        setError('No se pudo cargar el historial del producto.');
      } finally {
        setLoading(false);
      }
    };

    void load();
  }, [productId, reloadKey, fromDate, toDate]);

  let movementContent: ReactNode;
  if (loading) {
    movementContent = (
      <div className="catalog-loading kardex-loading">
        {[0, 1, 2].map((item) => (
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
  } else if (error) {
    movementContent = (
      <div className="catalog-error" role="alert">
        <strong>{error}</strong>
        <button
          type="button"
          className="secondary-button"
          onClick={() => setReloadKey((value) => value + 1)}
        >
          Reintentar
        </button>
      </div>
    );
  } else if (movements.length === 0) {
    movementContent = (
      <div className="empty-state kardex-empty">
        <div className="empty-icon"><Boxes size={28} /></div>
        <h3>Sin movimientos registrados</h3>
        <p>
          {fromDate || toDate
            ? 'No existen movimientos en el período seleccionado.'
            : 'Las entradas y salidas de este producto aparecerán aquí.'}
        </p>
      </div>
    );
  } else {
    movementContent = (
      <section className="kardex-card">
        <div className="kardex-summary">
          <div>
            <span>Movimientos</span>
            <strong>{movements.length}</strong>
          </div>
          <div>
            <span>Entradas</span>
            <strong>{movements.filter((movement) => movement.tipo === 'entrada').length}</strong>
          </div>
          <div>
            <span>Salidas</span>
            <strong>{movements.filter((movement) => movement.tipo === 'salida').length}</strong>
          </div>
        </div>

        <div className="kardex-table-container">
          <table className="kardex-table">
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Tipo</th>
                <th>Motivo</th>
                <th>Cantidad</th>
                <th>Stock anterior</th>
                <th>Stock resultante</th>
              </tr>
            </thead>
            <tbody>
              {movements.map((movement) => (
                <tr key={movement.id}>
                  <td>
                    <strong>{formatDate(movement.fecha)}</strong>
                    {movement.notas && <span className="movement-note">{movement.notas}</span>}
                  </td>
                  <td>
                    <span className={`movement-badge ${movement.tipo}`}>
                      {movement.tipo === 'entrada' ? 'Entrada' : 'Salida'}
                    </span>
                  </td>
                  <td>{movement.motivo}</td>
                  <td className={movement.tipo}>{movement.tipo === 'entrada' ? '+' : '-'}{movement.cantidad}</td>
                  <td>{movement.stock_anterior}</td>
                  <td><strong>{movement.stock_resultante}</strong></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    );
  }

  return (
    <main className="products-page create-product-page kardex-page">
      <div className="kardex-content">
        <header className="kardex-header">
          <div>
            <button
              type="button"
              className="back-button"
              onClick={() => void navigate('/productos')}
            >
              <ArrowLeft size={16} />
              Volver al catálogo
            </button>
            <button
              type="button"
              className="back-button kardex-home-button"
              onClick={() => void navigate('/home')}
            >
              <Home size={16} /> Inicio
            </button>
            <span className="eyebrow">Historial de inventario</span>
            <h1>{product?.nombre ?? 'Kardex del producto'}</h1>
            {product && (
              <p>
                Stock actual: <strong>{product.stock_actual}</strong> · Stock mínimo:{' '}
                <strong>{product.stock_minimo}</strong>
              </p>
            )}
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Actualizar kardex"
            onClick={() => setReloadKey((value) => value + 1)}
          >
            <RefreshCw size={18} />
          </button>
        </header>

        <section className="kardex-filters" aria-label="Filtros por fecha">
          <div className="filter-title">
            <CalendarDays size={18} />
            <div>
              <strong>Filtrar por período</strong>
              <span>Consulta movimientos dentro de un rango de fechas.</span>
            </div>
          </div>
          <label htmlFor="kardex-from-date">
            <span>Desde</span>
            <input
              id="kardex-from-date"
              type="date"
              value={fromDate}
              onChange={(event) => setFromDate(event.target.value)}
            />
          </label>
          <label htmlFor="kardex-to-date">
            <span>Hasta</span>
            <input
              id="kardex-to-date"
              type="date"
              value={toDate}
              onChange={(event) => setToDate(event.target.value)}
            />
          </label>
          {(fromDate || toDate) && (
            <button
              type="button"
              className="clear-date-filter"
              onClick={() => {
                setFromDate('');
                setToDate('');
                setFilterError('');
              }}
            >
              <X size={15} /> Limpiar
            </button>
          )}
          {filterError && <p className="filter-error" role="alert">{filterError}</p>}
        </section>

        {movementContent}
      </div>
    </main>
  );
}

export default ProductKardex;
