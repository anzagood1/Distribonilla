import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import ProductForm from '../../src/components/ProductForm';

afterEach(cleanup);

it('shows field-level validation and does not submit invalid values', () => {
  const onSubmit = vi.fn(async () => {});
  render(<ProductForm onSubmit={onSubmit} loading={false} />);

  fireEvent.click(screen.getByRole('button', { name: 'Crear producto' }));

  expect(screen.getByText('Ingresa el nombre del producto.')).toBeTruthy();
  expect(screen.getByText('Ingresa el precio unitario.')).toBeTruthy();
  expect(screen.getByLabelText(/Nombre del producto/).getAttribute('aria-invalid')).toBe('true');
  expect(onSubmit).not.toHaveBeenCalled();
});

it('uses zero when stock fields are left empty', async () => {
  const onSubmit = vi.fn(async () => {});
  render(<ProductForm onSubmit={onSubmit} loading={false} />);

  fireEvent.change(screen.getByLabelText(/Nombre del producto/), {
    target: { value: 'Producto sin stock' },
  });
  fireEvent.change(screen.getByLabelText(/Precio unitario/), {
    target: { value: '10' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Crear producto' }));

  expect(onSubmit).toHaveBeenCalledWith(
    expect.objectContaining({ stock_actual: 0, stock_minimo: 0 })
  );
});

it('rejects negative and fractional stock values', () => {
  const onSubmit = vi.fn(async () => {});
  render(<ProductForm onSubmit={onSubmit} loading={false} />);

  fireEvent.change(screen.getByLabelText(/Nombre del producto/), {
    target: { value: 'Camiseta básica' },
  });
  fireEvent.change(screen.getByLabelText(/Precio unitario/), {
    target: { value: '25.50' },
  });
  fireEvent.change(screen.getByLabelText('Stock actual'), {
    target: { value: '-1' },
  });
  fireEvent.change(screen.getByLabelText('Stock mínimo'), {
    target: { value: '1.5' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Crear producto' }));

  expect(screen.getAllByText('Usa un número entero igual o mayor que cero.')).toHaveLength(2);
  expect(onSubmit).not.toHaveBeenCalled();
});

it('submits a normalized product using essential and optional fields', async () => {
  const onSubmit = vi.fn(async () => {});
  render(<ProductForm onSubmit={onSubmit} loading={false} />);

  fireEvent.change(screen.getByLabelText(/Nombre del producto/), {
    target: { value: '  Camiseta básica  ' },
  });
  fireEvent.change(screen.getByLabelText(/Precio unitario/), {
    target: { value: '25.50' },
  });
  fireEvent.change(screen.getByLabelText('Stock actual'), {
    target: { value: '12' },
  });
  fireEvent.change(screen.getByLabelText('Stock mínimo'), {
    target: { value: '3' },
  });
  fireEvent.change(screen.getByLabelText('Descripción'), {
    target: { value: '  Algodón suave  ' },
  });
  fireEvent.change(screen.getByLabelText('Talla'), {
    target: { value: ' M ' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Crear producto' }));

  expect(onSubmit).toHaveBeenCalledWith({
    nombre: 'Camiseta básica',
    descripcion: 'Algodón suave',
    precio_unitario: 25.5,
    talla: 'M',
    stock_actual: 12,
    stock_minimo: 3,
    aplica_iva: true,
  });
});
