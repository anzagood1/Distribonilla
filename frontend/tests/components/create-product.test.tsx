import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import CreateProduct from '../../src/pages/CreateProduct';

const mocks = vi.hoisted(() => ({ createProduct: vi.fn(), navigate: vi.fn() }));
vi.mock('../../src/services/productService', () => ({ createProduct: mocks.createProduct }));
vi.mock('react-router-dom', () => ({ useNavigate: () => mocks.navigate }));

beforeEach(() => vi.resetAllMocks());
afterEach(cleanup);

function fillForm() {
  fireEvent.change(screen.getByLabelText(/Nombre del producto/), { target: { value: '  Camiseta  ' } });
  fireEvent.change(screen.getByLabelText(/Precio unitario/), { target: { value: '20' } });
  fireEvent.click(screen.getByRole('button', { name: 'Crear producto' }));
}

it('creates a normalized product and navigates to the catalog', async () => {
  mocks.createProduct.mockResolvedValue({ id: 8 });
  render(<CreateProduct />);
  fillForm();
  await waitFor(() => expect(mocks.createProduct).toHaveBeenCalledWith(expect.objectContaining({
    nombre: 'Camiseta', precio_unitario: 20, stock_actual: 0,
  })));
  await waitFor(() => expect(mocks.navigate).toHaveBeenCalledWith('/productos'));
});

it('keeps the form available and shows a safe message when creation fails', async () => {
  const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
  try {
    mocks.createProduct.mockRejectedValue(new Error('PRIVATE_FIXTURE'));
    render(<CreateProduct />);
    fillForm();
    await waitFor(() => expect(screen.getByText(/No se pudo crear el producto/)).toBeTruthy());
    expect(document.body.textContent).not.toContain('PRIVATE_FIXTURE');
    expect(mocks.navigate).not.toHaveBeenCalled();
    expect((screen.getByRole('button', { name: 'Crear producto' }) as HTMLButtonElement).disabled).toBe(false);
  } finally {
    consoleError.mockRestore();
  }
});
