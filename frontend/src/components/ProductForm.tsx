import { useMemo, useState } from 'react';
import type { SubmitEvent } from 'react';
import { AlertCircle, LoaderCircle } from 'lucide-react';
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
  const [stockActual, setStockActual] = useState('');
  const [stockMinimo, setStockMinimo] = useState('');
  const [aplicaIva, setAplicaIva] = useState(true);
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const errors = useMemo(() => {
    const nextErrors: Record<string, string> = {};
    const name = nombre.trim();
    const price = Number(precio);
    const currentStock = Number(stockActual);
    const minimumStock = Number(stockMinimo);

    if (!name) nextErrors.nombre = 'Ingresa el nombre del producto.';
    else if (name.length < 2) nextErrors.nombre = 'Usa al menos 2 caracteres.';
    if (descripcion.trim().length > 300) {
      nextErrors.descripcion = 'La descripción no puede superar 300 caracteres.';
    }
    if (!precio) nextErrors.precio = 'Ingresa el precio unitario.';
    else if (!Number.isFinite(price) || price <= 0) {
      nextErrors.precio = 'El precio debe ser mayor que cero.';
    } else if (price > 999999999) {
      nextErrors.precio = 'El precio excede el límite permitido.';
    }
    if (talla.trim().length > 10) {
      nextErrors.talla = 'La talla no puede superar 10 caracteres.';
    }
    if (stockActual !== '' && (!Number.isInteger(currentStock) || currentStock < 0)) {
      nextErrors.stockActual = 'Usa un número entero igual o mayor que cero.';
    }
    if (stockMinimo !== '' && (!Number.isInteger(minimumStock) || minimumStock < 0)) {
      nextErrors.stockMinimo = 'Usa un número entero igual o mayor que cero.';
    }

    return nextErrors;
  }, [nombre, descripcion, precio, talla, stockActual, stockMinimo]);

  const markTouched = (field: string) => {
    setTouched((current) => ({ ...current, [field]: true }));
  };

  const fieldError = (field: string) =>
    touched[field] ? errors[field] : undefined;

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>): void => {
    event.preventDefault();
    setTouched({
      nombre: true,
      descripcion: true,
      precio: true,
      talla: true,
      stockActual: true,
      stockMinimo: true,
    });

    if (Object.keys(errors).length > 0) {
      const fieldIds: Record<string, string> = {
        nombre: 'nombre',
        descripcion: 'descripcion',
        precio: 'precio',
        talla: 'talla',
        stockActual: 'stockActual',
        stockMinimo: 'stockMinimo',
      };
      const firstError = Object.keys(errors)[0];
      document.getElementById(fieldIds[firstError])?.focus();
      return;
    }

    void onSubmit({
      nombre: nombre.trim(),
      descripcion: descripcion.trim() || null,
      precio_unitario: Number(precio),
      talla: talla.trim() || null,
      stock_actual: stockActual === '' ? 0 : Number(stockActual),
      stock_minimo: stockMinimo === '' ? 0 : Number(stockMinimo),
      aplica_iva: aplicaIva,
    });
  };

  return (
    <form className="product-form" onSubmit={handleSubmit} noValidate>
      <div className="form-grid">
        <div className="form-group">
          <label htmlFor="nombre">Nombre del producto <span>*</span></label>
          <input
            id="nombre"
            type="text"
            value={nombre}
            onChange={(event) => setNombre(event.target.value)}
            onBlur={() => markTouched('nombre')}
            placeholder="Ej. Camiseta básica"
            maxLength={150}
            required
            aria-invalid={Boolean(fieldError('nombre'))}
            aria-describedby={fieldError('nombre') ? 'nombre-error' : 'nombre-help'}
          />
          {fieldError('nombre') ? (
            <span className="field-error" id="nombre-error" role="alert">
              <AlertCircle size={14} /> {fieldError('nombre')}
            </span>
          ) : (
            <span className="field-help" id="nombre-help">Nombre corto y fácil de reconocer.</span>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="precio">Precio unitario <span>*</span></label>
          <input
            id="precio"
            type="number"
            value={precio}
            onChange={(event) => setPrecio(event.target.value)}
            onBlur={() => markTouched('precio')}
            placeholder="0.00"
            min="0.01"
            max="999999999"
            step="0.01"
            required
            aria-invalid={Boolean(fieldError('precio'))}
            aria-describedby={fieldError('precio') ? 'precio-error' : 'precio-help'}
          />
          {fieldError('precio') ? (
            <span className="field-error" id="precio-error" role="alert">
              <AlertCircle size={14} /> {fieldError('precio')}
            </span>
          ) : (
            <span className="field-help" id="precio-help">Valor de venta sin símbolos.</span>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="stockActual">Stock actual</label>
          <input
            id="stockActual"
            type="number"
            value={stockActual}
            onChange={(event) => setStockActual(event.target.value)}
            onBlur={() => markTouched('stockActual')}
            placeholder="0"
            min="0"
            step="1"
            required
            aria-invalid={Boolean(fieldError('stockActual'))}
            aria-describedby={fieldError('stockActual') ? 'stockActual-error' : 'stockActual-help'}
          />
          {fieldError('stockActual') ? (
            <span className="field-error" id="stockActual-error" role="alert">
              <AlertCircle size={14} /> {fieldError('stockActual')}
            </span>
          ) : (
            <span className="field-help" id="stockActual-help">Cantidad disponible actualmente.</span>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="stockMinimo">Stock mínimo</label>
          <input
            id="stockMinimo"
            type="number"
            value={stockMinimo}
            onChange={(event) => setStockMinimo(event.target.value)}
            onBlur={() => markTouched('stockMinimo')}
            placeholder="0"
            min="0"
            step="1"
            required
            aria-invalid={Boolean(fieldError('stockMinimo'))}
            aria-describedby={fieldError('stockMinimo') ? 'stockMinimo-error' : 'stockMinimo-help'}
          />
          {fieldError('stockMinimo') ? (
            <span className="field-error" id="stockMinimo-error" role="alert">
              <AlertCircle size={14} /> {fieldError('stockMinimo')}
            </span>
          ) : (
            <span className="field-help" id="stockMinimo-help">Aviso cuando quede por debajo.</span>
          )}
        </div>
      </div>

      <div className="form-grid optional-grid">
        <div className="form-group description-group">
          <label htmlFor="descripcion">Descripción</label>
          <textarea
            id="descripcion"
            value={descripcion}
            onChange={(event) => setDescripcion(event.target.value)}
            onBlur={() => markTouched('descripcion')}
            placeholder="Describe las características del producto"
            rows={3}
            maxLength={300}
            aria-invalid={Boolean(fieldError('descripcion'))}
            aria-describedby="descripcion-help"
          />
          <span className="field-help" id="descripcion-help">
            {descripcion.length}/300 caracteres
          </span>
          {fieldError('descripcion') && (
            <span className="field-error" role="alert">
              <AlertCircle size={14} /> {fieldError('descripcion')}
            </span>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="talla">Talla</label>
          <input
            id="talla"
            type="text"
            value={talla}
            onChange={(event) => setTalla(event.target.value)}
            onBlur={() => markTouched('talla')}
            placeholder="Ej. M, L, 32"
            maxLength={10}
            aria-invalid={Boolean(fieldError('talla'))}
            aria-describedby="talla-help"
          />
          <span className="field-help" id="talla-help">Ropa, calzado o medida.</span>
        </div>

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
        <button type="submit" className="primary-button" disabled={loading}>
          {loading ? (
            <><LoaderCircle className="spin" size={17} /> Guardando...</>
          ) : (
            'Crear producto'
          )}
        </button>
      </div>
    </form>
  );
}

export default ProductForm;
