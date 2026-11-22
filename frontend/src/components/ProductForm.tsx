import { useState } from 'react';
import type { ComponentProps } from 'react';
import type { ProductCreate } from '../types/product';

interface ProductFormProps {
  readonly onSubmit: (product: ProductCreate) => Promise<void>;
  readonly loading: boolean;
}

function ProductForm({ onSubmit, loading }: ProductFormProps) {
  const [nombre, setNombre] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [precio, setPrecio] = useState('');
  const [talla, setTalla] = useState('');
  const [stockActual, setStockActual] = useState('0');
  const [stockMinimo, setStockMinimo] = useState('0');
  const [aplicaIva, setAplicaIva] = useState(true);

  const handleSubmit: NonNullable<ComponentProps<'form'>['onSubmit']> = async (event) => {
    event.preventDefault();

    const product: ProductCreate = {
      nombre: nombre.trim(),
      descripcion: descripcion.trim() || null,
      precio_unitario: Number(precio),
      talla: talla.trim() || null,
      stock_actual: Number(stockActual),
      stock_minimo: Number(stockMinimo),
      aplica_iva: aplicaIva,
    };

    await onSubmit(product);
  };

  return (
    <form className="product-form" onSubmit={handleSubmit}>
      <div className="form-section">
        <h3>Información del producto</h3>

        <div className="form-group">
          <label htmlFor="nombre">Nombre del producto *</label>
          <input
            id="nombre"
            type="text"
            value={nombre}
            onChange={(event) => setNombre(event.target.value)}
            placeholder="Ej. Camiseta básica"
            maxLength={150}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="descripcion">Descripción</label>
          <textarea
            id="descripcion"
            value={descripcion}
            onChange={(event) => setDescripcion(event.target.value)}
            placeholder="Describe las características del producto"
            rows={3}
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="precio">Precio unitario *</label>
            <input
              id="precio"
              type="number"
              value={precio}
              onChange={(event) => setPrecio(event.target.value)}
              placeholder="0.00"
              min="0.01"
              step="0.01"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="talla">Talla</label>
            <input
              id="talla"
              type="text"
              value={talla}
              onChange={(event) => setTalla(event.target.value)}
              placeholder="Ej. M, L, 32"
              maxLength={10}
            />
          </div>
        </div>
      </div>

      <div className="form-section">
        <h3>Inventario</h3>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="stockActual">Stock actual</label>
            <input
              id="stockActual"
              type="number"
              value={stockActual}
              onChange={(event) => setStockActual(event.target.value)}
              min="0"
              step="1"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="stockMinimo">Stock mínimo</label>
            <input
              id="stockMinimo"
              type="number"
              value={stockMinimo}
              onChange={(event) => setStockMinimo(event.target.value)}
              min="0"
              step="1"
              required
            />
          </div>
        </div>
      </div>

      <div className="form-section">
        <h3>Impuestos</h3>

        <label className="checkbox-container">
          <input
            type="checkbox"
            checked={aplicaIva}
            onChange={(event) => setAplicaIva(event.target.checked)}
          />
          <span>Este producto aplica IVA</span>
        </label>
      </div>

      <div className="form-actions">
        <button
          type="submit"
          className="primary-button"
          disabled={loading}
        >
          {loading ? 'Guardando...' : 'Crear producto'}
        </button>
      </div>
    </form>
  );
}

export default ProductForm;