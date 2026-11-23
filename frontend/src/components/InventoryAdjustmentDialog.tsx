import { useEffect, useRef, useState, type SubmitEvent } from 'react';
import { isAxiosError } from 'axios';
import { X } from 'lucide-react';
import {
  registerInventoryEntry,
  registerInventoryExit,
} from '../services/productService';
import type {
  InventoryEntryCreate,
  InventoryExitCreate,
  Product,
} from '../types/product';

export type InventoryAdjustmentType = 'entrada' | 'salida';

interface InventoryAdjustmentDialogProps {
  readonly product: Product;
  readonly type: InventoryAdjustmentType;
  readonly onClose: () => void;
  readonly onSaved: () => void;
}

function isExitReason(reason: string): reason is InventoryExitCreate['motivo'] {
  return reason === 'merma' || reason === 'daño' || reason === 'ajuste';
}

function getValidationError(
  type: InventoryAdjustmentType,
  amount: number,
  stock: number,
  reason: string
): string | null {
  if (!Number.isSafeInteger(amount) || amount <= 0) {
    return 'Ingresa una cantidad entera mayor que cero.';
  }
  if (type === 'salida' && amount > stock) {
    return `Solo hay ${stock} unidades disponibles.`;
  }
  if (type === 'entrada' && !reason.trim()) {
    return 'Indica el motivo de la entrada.';
  }
  if (type === 'salida' && !isExitReason(reason)) {
    return 'Selecciona un motivo válido para la salida.';
  }
  return null;
}

async function sendAdjustment(
  type: InventoryAdjustmentType,
  request: InventoryEntryCreate
): Promise<void> {
  if (type === 'entrada') {
    await registerInventoryEntry(request);
    return;
  }
  if (!isExitReason(request.motivo)) {
    throw new Error('El motivo de salida no es válido.');
  }
  const exit: InventoryExitCreate = { ...request, motivo: request.motivo };
  await registerInventoryExit(exit);
}

function getRequestErrorMessage(error: unknown): string {
  if (!isAxiosError(error)) {
    console.error('Error al ajustar el inventario:', error);
    return 'No se pudo actualizar el inventario. Inténtalo de nuevo.';
  }
  const detail = error.response?.data?.detail;
  return typeof detail === 'string'
    ? detail
    : 'No se pudo actualizar el inventario. Inténtalo de nuevo.';
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
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    dialogRef.current?.showModal();
  }, []);

  const submitAdjustment = async (): Promise<void> => {
    const amount = Number(quantity);
    const validationError = getValidationError(
      type,
      amount,
      product.stock_actual,
      reason
    );
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    setError('');
    try {
      const request: InventoryEntryCreate = {
        producto_id: product.id,
        cantidad: amount,
        motivo: reason,
        notas: notes.trim() || null,
      };
      await sendAdjustment(type, request);
      onSaved();
    } catch (requestError) {
      setError(getRequestErrorMessage(requestError));
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
    <dialog
      ref={dialogRef}
      className="inventory-adjustment-dialog"
      aria-labelledby="inventory-adjustment-title"
      onClose={onClose}
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
          <span className="inventory-adjustment-label">Cantidad</span>
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
            <span className="inventory-adjustment-label">Motivo</span>
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
            <span className="inventory-adjustment-label">Motivo</span>
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
          <span className="inventory-adjustment-label">Notas (opcional)</span>
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
    </dialog>
  );
}

export default InventoryAdjustmentDialog;
