import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import ProductKardex from '../../src/pages/ProductKardex';

const mocks = vi.hoisted(() => ({
  getProducts: vi.fn(),
  getProductMovements: vi.fn(),
  navigate: vi.fn(),
  productId: '8',
}));

vi.mock('../../src/services/productService', () => ({
  getProducts: mocks.getProducts,
  getProductMovements: mocks.getProductMovements,
}));
vi.mock('react-router-dom', () => ({
  useNavigate: () => mocks.navigate,
  useParams: () => ({ productId: mocks.productId }),
}));

const product = {
  id: 8, nombre: 'Camiseta', descripcion: null, categoria_id: null,
  precio_unitario: 20, talla: 'M', stock_actual: 5, stock_minimo: 2,
  aplica_iva: true,
};
const movement = {
  id: 1, producto_id: 8, tipo: 'salida', cantidad: 4, motivo: 'merma',
  notas: 'Prueba', fecha: '2026-11-22T12:00:00Z', usuario_id: 3,
  stock_anterior: 5, stock_resultante: 1,
};

beforeEach(() => {
  vi.resetAllMocks();
  mocks.productId = '8';
  mocks.getProducts.mockResolvedValue([product]);
  mocks.getProductMovements.mockResolvedValue([movement]);
});
afterEach(cleanup);

it('loads a product movement with stock history and navigates back', async () => {
  render(<ProductKardex />);
  expect(await screen.findByText('merma')).toBeTruthy();
  expect(screen.getByRole('heading', { name: 'Camiseta' })).toBeTruthy();
  expect(screen.getByText('Prueba')).toBeTruthy();
  expect(mocks.getProductMovements).toHaveBeenCalledWith(8, '', '');
  fireEvent.click(screen.getByRole('button', { name: /Volver al cat/ }));
  fireEvent.click(screen.getByRole('button', { name: 'Inicio' }));
  expect(mocks.navigate).toHaveBeenCalledWith('/productos');
  expect(mocks.navigate).toHaveBeenCalledWith('/home');
});

it('filters movements by date and clears the selected range', async () => {
  render(<ProductKardex />);
  await screen.findByText('merma');
  fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-11-01' } });
  fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-11-22' } });
  await waitFor(() => expect(mocks.getProductMovements).toHaveBeenCalledWith(8, '2026-11-01', '2026-11-22'));
  fireEvent.click(screen.getByRole('button', { name: /Limpiar/ }));
  await waitFor(() => expect(mocks.getProductMovements).toHaveBeenCalledWith(8, '', ''));
});

it('rejects an inverted date range before requesting movements', async () => {
  render(<ProductKardex />);
  await screen.findByText('merma');
  fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-12-01' } });
  fireEvent.change(screen.getByLabelText('Hasta'), { target: { value: '2026-11-01' } });
  expect(await screen.findByRole('alert')).toBeTruthy();
  expect(mocks.getProductMovements).not.toHaveBeenCalledWith(8, '2026-12-01', '2026-11-01');
});

it('shows an empty state when the product has no movements', async () => {
  mocks.getProductMovements.mockResolvedValue([]);
  render(<ProductKardex />);
  expect(await screen.findByText('Sin movimientos registrados')).toBeTruthy();
  expect(screen.getByRole('heading', { name: 'Camiseta' })).toBeTruthy();
});

it('reports a load failure and retries successfully', async () => {
  const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
  try {
    mocks.getProductMovements.mockRejectedValueOnce(new Error('fixture'));
    render(<ProductKardex />);
    expect(await screen.findByRole('alert')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByText('merma')).toBeTruthy();
  } finally {
    consoleError.mockRestore();
  }
});
