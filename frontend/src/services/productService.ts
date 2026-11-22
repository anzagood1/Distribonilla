import axios from 'axios';
import type { Product, ProductCreate } from '../types/product';

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_URL?.replace(/\/$/, '') ||
    'http://127.0.0.1:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

export async function getProducts(): Promise<Product[]> {
  const response = await api.get<Product[]>('/api/v1/inventory/items/');
  return response.data;
}

export async function createProduct(
  product: ProductCreate
): Promise<Product> {
  const response = await api.post<Product>(
    '/api/v1/inventory/items/',
    product
  );

  return response.data;
}