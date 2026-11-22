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