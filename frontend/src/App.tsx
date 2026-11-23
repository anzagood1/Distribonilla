import { Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute, PublicOnlyRoute } from './auth/ProtectedRoute';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import ProductCatalog from './pages/ProductCatalog';
import CreateProduct from './pages/CreateProduct';
import ProductKardex from './pages/ProductKardex';

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<LoginPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route path="/home" element={<HomePage />} />
          <Route path="/productos" element={<ProductCatalog />} />
          <Route path="/productos/nuevo" element={<CreateProduct />} />
          <Route path="/productos/:productId/kardex" element={<ProductKardex />} />
        </Route>

        <Route path="/" element={<Navigate to="/productos" replace />} />
        <Route path="*" element={<Navigate to="/productos" replace />} />
      </Routes>
    </AuthProvider>
  );
}

export default App;