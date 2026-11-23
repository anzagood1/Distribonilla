import { beforeEach, expect, it, vi } from 'vitest';
import {
  createProduct,
  getProductMovements,
  getProducts,
  registerInventoryEntry,
  registerInventoryExit,
} from '../../src/services/productService';

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  requestUse: vi.fn(),
  getSession: vi.fn(),
}));

vi.mock('axios', () => ({
  default: {
    create: () => ({
      get: mocks.get,
      post: mocks.post,
      interceptors: { request: { use: mocks.requestUse } },
    }),
  },
}));
vi.mock('../../src/utils/supabase', () => ({
  supabase: { auth: { getSession: mocks.getSession } },
}));

const interceptor = mocks.requestUse.mock.calls[0][0] as (config: { headers: Record<string, string> }) => Promise<{ headers: Record<string, string> }>;

beforeEach(() => {
  vi.clearAllMocks();
  mocks.get.mockResolvedValue({ data: [] });
  mocks.post.mockResolvedValue({ data: { id: 8 } });
});

it('uses catalog and Kardex routes with date filters', async () => {
  expect(await getProducts()).toEqual([]);
  expect(await getProductMovements(8, '2026-11-01', '2026-11-22')).toEqual([]);
  expect(mocks.get).toHaveBeenCalledWith('/api/v1/inventory/items/');
  expect(mocks.get).toHaveBeenCalledWith('/api/v1/inventory/items/8/movements', {
    params: { from_date: '2026-11-01', to_date: '2026-11-22' },
  });
});

it('posts product creation and inventory movements with distinct retry keys', async () => {
  const product = { nombre: 'Camiseta', precio_unitario: 20, stock_actual: 0, stock_minimo: 0, aplica_iva: true };
  const entry = { producto_id: 8, cantidad: 4, motivo: 'compra', notas: null };
  const exit = { producto_id: 8, cantidad: 2, motivo: 'merma' as const, notas: null };
  await createProduct(product);
  await registerInventoryEntry(entry);
  await registerInventoryExit(exit);
  expect(mocks.post).toHaveBeenNthCalledWith(1, '/api/v1/inventory/items/', product);
  expect(mocks.post).toHaveBeenNthCalledWith(2, '/api/v1/inventory/entries', entry, {
    headers: { 'Idempotency-Key': expect.any(String) },
  });
  expect(mocks.post).toHaveBeenNthCalledWith(3, '/api/v1/inventory/exits', exit, {
    headers: { 'Idempotency-Key': expect.any(String) },
  });
  const entryKey = mocks.post.mock.calls[1][2].headers['Idempotency-Key'];
  const exitKey = mocks.post.mock.calls[2][2].headers['Idempotency-Key'];
  expect(entryKey).not.toBe(exitKey);
});

it('attaches an access token only when a session exists', async () => {
  mocks.getSession.mockResolvedValueOnce({ data: { session: null } });
  expect((await interceptor({ headers: {} })).headers.Authorization).toBeUndefined();
  mocks.getSession.mockResolvedValueOnce({ data: { session: { access_token: 'fixture-token' } } });
  expect((await interceptor({ headers: {} })).headers.Authorization).toBe('Bearer fixture-token');
});
