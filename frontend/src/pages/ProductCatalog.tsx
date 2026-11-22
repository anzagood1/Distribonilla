import { useEffect, useMemo, useState } from 'react';
import { getProducts } from '../services/productService';
import type { Product } from '../types/product';

function ProductCatalog() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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
  }, []);

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
      return <div className="empty-state">Cargando productos...</div>;
    }

    if (error) {
      return <div className="error-message">{error}</div>;
    }

    if (filteredProducts.length === 0) {
      return (
        <div className="empty-state">
          {search
            ? 'No se encontraron productos con esa búsqueda.'
            : 'Todavía no hay productos registrados.'}
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
            </tr>
          </thead>

          <tbody>
            {filteredProducts.map((product) => (
              <tr key={product.id}>
                <td>#{product.id}</td>
                <td className="product-name">{product.nombre}</td>
                <td>{product.descripcion || '—'}</td>
                <td>{product.talla || '—'}</td>
                <td>${Number(product.precio_unitario).toFixed(2)}</td>
                <td>{product.stock_actual}</td>
                <td>{product.stock_minimo}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <>
      <input
        type="search"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Buscar por ID o producto"
        aria-label="Buscar productos por ID o nombre"
      />
      {renderCatalog()}
    </>
  );
}

export default ProductCatalog;