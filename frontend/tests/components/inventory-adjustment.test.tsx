import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import ProductCatalog from '../../src/pages/ProductCatalog';

const mocks = vi.hoisted(() => ({
  getProducts: vi.fn(),
  registerInventoryEntry: vi.fn(),
  registerInventoryExit: vi.fn(),
  navigate: vi.fn(),
}));

vi.mock('../../src/services/productService', () => ({
  getProducts: mocks.getProducts,
  registerInventoryEntry: mocks.registerInventoryEntry,
  registerInventoryExit: mocks.registerInventoryExit,
}));

vi.mock('react-router-dom', () => ({
  useNavigate: () => mocks.navigate,
}));

const product = {
  id: 8,
  nombre: 'Camiseta',
  descripcion: null,
  categoria_id: null,
  precio_unitario: 20,
  talla: 'M',
  stock_actual: 8,
  stock_minimo: 2,
  aplica_iva: true,
};

beforeEach(() => {
  vi.resetAllMocks();
  mocks.getProducts.mockResolvedValue([product]);
  mocks.registerInventoryEntry.mockResolvedValue({});
  mocks.registerInventoryExit.mockResolvedValue({});
});

afterEach(cleanup);

it('increases stock from the catalog and reloads the product list', async () => {
  render(<ProductCatalog />);
  fireEvent.click(await screen.findByRole('button', { name: 'Aumentar stock de Camiseta' }));
  fireEvent.change(screen.getByLabelText('Cantidad'), { target: { value: '5' } });
  fireEvent.change(screen.getByLabelText('Motivo'), { target: { value: 'Compra' } });
  fireEvent.click(screen.getByRole('button', { name: 'Aumentar stock' }));

  await waitFor(() => {
    expect(mocks.registerInventoryEntry).toHaveBeenCalledWith({
      producto_id: 8,
      cantidad: 5,
      motivo: 'Compra',
      notas: null,
    });
  });
  await waitFor(() => expect(mocks.getProducts).toHaveBeenCalledTimes(2));
  expect(screen.queryByRole('dialog')).toBeNull();
});

it('decreases stock with a valid exit reason', async () => {
  render(<ProductCatalog />);
  fireEvent.click(await screen.findByRole('button', { name: 'Disminuir stock de Camiseta' }));
  fireEvent.change(screen.getByLabelText('Cantidad'), { target: { value: '3' } });
  fireEvent.change(screen.getByLabelText('Motivo'), { target: { value: 'merma' } });
  fireEvent.click(screen.getByRole('button', { name: 'Disminuir stock' }));

  await waitFor(() => {
    expect(mocks.registerInventoryExit).toHaveBeenCalledWith({
      producto_id: 8,
      cantidad: 3,
      motivo: 'merma',
      notas: null,
    });
  });
});

it('prevents an exit larger than the current stock', async () => {
  render(<ProductCatalog />);
  fireEvent.click(await screen.findByRole('button', { name: 'Disminuir stock de Camiseta' }));
  fireEvent.change(screen.getByLabelText('Cantidad'), { target: { value: '9' } });
  fireEvent.click(screen.getByRole('button', { name: 'Disminuir stock' }));

  expect((await screen.findByRole('alert')).textContent).toContain(
    'Solo hay 8 unidades disponibles.'
  );
  expect(mocks.registerInventoryExit).not.toHaveBeenCalled();
});
