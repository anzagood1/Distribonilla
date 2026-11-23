import { useState, type SubmitEvent } from 'react';
import { isAxiosError } from 'axios';
import { X } from 'lucide-react';
import {
  registerInventoryEntry,
  registerInventoryExit,
} from '../services/productService';
import type { Product } from '../types/product';

export type InventoryAdjustmentType = 'entrada' | 'salida';

interface InventoryAdjustmentDialogProps {
  readonly product: Product;
  readonly type: InventoryAdjustmentType;
  readonly onClose: () => void;
  readonly onSaved: () => void;
}

function InventoryAdjustmentDialog({
  product,
  type,
  onClose,
  onSaved,
}: InventoryAdjustmentDialogProps) {
  const [quantity, setQuantity] = useState('');
  const [reason, setReason] = useState(type === 'salida' ? 'ajuste' : '');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const submitAdjustment = async () => {
    const amount = Number(quantity);
    if (!Number.isSafeInteger(amount) || amount <= 0) {
      setError('Ingresa una cantidad entera mayor que cero.');
      return;
    }
    if (type === 'salida' && amount > product.stock_actual) {
      setError(`Solo hay ${product.stock_actual} unidades disponibles.`);
      return;
    }
    if (type === 'entrada' && !reason.trim()) {
      setError('Indica el motivo de la entrada.');
      return;
    }

    setSaving(true);
    setError('');
    try {
      const request = {
        producto_id: product.id,
        cantidad: amount,
        motivo: reason,
        notas: notes.trim() || null,
      };
      if (type === 'entrada') {
        await registerInventoryEntry(request);
      } else {
        if (reason !== 'merma' && reason !== 'daño' && reason !== 'ajuste') {
          setError('Selecciona un motivo válido para la salida.');
          return;
        }
        await registerInventoryExit({
          ...request,
          motivo: reason,
        });
      }
      onSaved();
    } catch (requestError) {
      if (isAxiosError(requestError)) {
        const detail = requestError.response?.data?.detail;
        setError(
          typeof detail === 'string'
            ? detail
            : 'No se pudo actualizar el inventario. Inténtalo de nuevo.'
        );
      } else {
        console.error('Error al ajustar el inventario:', requestError);
        setError('No se pudo actualizar el inventario. Inténtalo de nuevo.');
      }
    } finally {
      setSaving(false);
    }
  };

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>): void => {
    event.preventDefault();
    void submitAdjustment();
  };

  const title = type === 'entrada' ? 'Aumentar stock' : 'Disminuir stock';

  return (
    <div
      className="inventory-adjustment-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !saving) onClose();
      }}
    >
      <section
        className="inventory-adjustment-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="inventory-adjustment-title"
      >
        <header className="inventory-adjustment-header">
          <div>
            <span className="eyebrow">Inventario</span>
            <h2 id="inventory-adjustment-title">{title}</h2>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Cerrar"
            onClick={onClose}
            disabled={saving}
          >
            <X size={18} />
          </button>
        </header>

        <p className="inventory-adjustment-product">
          {product.nombre} · Stock actual: <strong>{product.stock_actual}</strong>
        </p>

        <form className="inventory-adjustment-form" onSubmit={handleSubmit} noValidate>
          <label htmlFor="inventory-adjustment-quantity">
            Cantidad
            <input
              id="inventory-adjustment-quantity"
              type="number"
              min="1"
              max={type === 'salida' ? product.stock_actual : undefined}
              step="1"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              required
              autoFocus
            />
          </label>

          {type === 'entrada' ? (
            <label htmlFor="inventory-adjustment-reason">
              Motivo
              <input
                id="inventory-adjustment-reason"
                type="text"
                maxLength={500}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Ej. Compra o devolución"
                required
              />
            </label>
          ) : (
            <label htmlFor="inventory-adjustment-reason">
              Motivo
              <select
                id="inventory-adjustment-reason"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              >
                <option value="ajuste">Ajuste</option>
                <option value="merma">Merma</option>
                <option value="daño">Daño</option>
              </select>
            </label>
          )}

          <label htmlFor="inventory-adjustment-notes">
            Notas (opcional)
            <textarea
              id="inventory-adjustment-notes"
              maxLength={2000}
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={3}
            />
          </label>

          {error && <p className="inventory-adjustment-error" role="alert">{error}</p>}

          <div className="inventory-adjustment-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={onClose}
              disabled={saving}
            >
              Cancelar
            </button>
            <button type="submit" className="primary-button" disabled={saving}>
              {saving ? 'Guardando…' : title}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export default InventoryAdjustmentDialog;
