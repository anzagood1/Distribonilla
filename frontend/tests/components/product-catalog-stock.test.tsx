import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import ProductCatalog from '../../src/pages/ProductCatalog';

const mocks = vi.hoisted(() => ({
  getProducts: vi.fn(),
  navigate: vi.fn(),
}));

vi.mock('../../src/services/productService', () => ({
  getProducts: mocks.getProducts,
}));

vi.mock('react-router-dom', () => ({
  useNavigate: () => mocks.navigate,
}));

function product(stockActual: number, stockMinimo: number) {
  return {
    id: 8,
    nombre: 'Camiseta',
    descripcion: null,
    categoria_id: null,
    precio_unitario: 20,
    talla: 'M',
    stock_actual: stockActual,
    stock_minimo: stockMinimo,
    aplica_iva: true,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(cleanup);

it.each([
  { stockActual: 2, stockMinimo: 3, expectedClass: 'stock-low', expectedAlert: true },
  { stockActual: 3, stockMinimo: 3, expectedClass: 'stock-low', expectedAlert: true },
  { stockActual: 4, stockMinimo: 3, expectedClass: 'stock-ok', expectedAlert: false },
])(
  'TC-INV-14 equivalence class: stock=$stockActual, minimum=$stockMinimo',
  async ({ stockActual, stockMinimo, expectedClass, expectedAlert }) => {
    mocks.getProducts.mockResolvedValue([product(stockActual, stockMinimo)]);

    render(<ProductCatalog />);

    const badge = await screen.findByText(`${stockActual} unidades`);
    expect(badge.classList.contains(expectedClass)).toBe(true);
    expect(badge.classList.contains(expectedAlert ? 'stock-low' : 'stock-ok')).toBe(true);

    await waitFor(() => {
      const stockLowMetric = screen.getByText('Stock bajo').closest('article');
      expect(stockLowMetric?.textContent).toContain(expectedAlert ? '1' : '0');
    });
  },
);
