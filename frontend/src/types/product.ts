export interface Product {
  id: number;
  nombre: string;
  descripcion: string | null;
  categoria_id: number | null;
  precio_unitario: number;
  talla: string | null;
  stock_actual: number;
  stock_minimo: number;
  aplica_iva: boolean;
}

export interface ProductCreate {
  nombre: string;
  descripcion?: string | null;
  precio_unitario: number;
  talla?: string | null;
  stock_actual: number;
  stock_minimo: number;
  aplica_iva: boolean;
}

export interface InventoryMovement {
  id: number;
  producto_id: number;
  tipo: 'entrada' | 'salida';
  cantidad: number;
  motivo: string;
  notas: string | null;
  fecha: string;
  usuario_id: number;
  stock_anterior: number;
  stock_resultante: number;
}