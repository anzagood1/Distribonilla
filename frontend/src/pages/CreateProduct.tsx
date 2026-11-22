import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ProductForm from '../components/ProductForm';
import { createProduct } from '../services/productService';
import type { ProductCreate } from '../types/product';

function CreateProduct() {
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleCreateProduct = async (product: ProductCreate) => {
    try {
      setLoading(true);
      setError('');

      await createProduct(product);

      void navigate('/productos');
    } catch (err: unknown) {
      console.error('Error al crear el producto:', err);

      setError('No se pudo crear el producto. Verifica los datos e inténtalo nuevamente.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="products-page">
      <div className="page-header">
        <div>
          <button
            className="back-button"
            onClick={() => void navigate('/productos')}
            type="button"
          >
            ← Volver al catálogo
          </button>

          <h1>Crear producto</h1>
          <p>Registra un nuevo producto en el catálogo.</p>
        </div>
      </div>

      <section className="form-card">
        {error && <div className="error-message">{error}</div>}

        <ProductForm
          onSubmit={handleCreateProduct}
          loading={loading}
        />
      </section>
    </main>
  );
}

export default CreateProduct;