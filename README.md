# Distribonilla

Plataforma integral para la gestión de inventarios y facturación de distribonilla. Este proyecto está estructurado separando la lógica del cliente (Frontend) y del servidor (Backend), pero manteniendo todo bajo un mismo control de versiones para facilitar el desarrollo continuo y la sincronización del equipo.

---

## 🛠️ Stack Tecnológico

### Backend
* **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python) - *Elegido por su alto rendimiento y validación automática de datos con Pydantic.*
* **Base de Datos:** [PostgreSQL](https://www.postgresql.org/) alojado en [Supabase](https://supabase.com/).
* **ORM & Migraciones:** [SQLAlchemy](https://www.sqlalchemy.org/) para manejo de datos y [Alembic](https://alembic.sqlalchemy.org/en/latest/) para el control de versiones de la base de datos.
* **Autenticación:** Supabase Auth (JWT validado en FastAPI).

### Frontend
* **Framework:** [React 18](https://react.dev/) con [TypeScript](https://www.typescriptlang.org/).
* **Build Tool:** [Vite](https://vitejs.dev/) - *Para tiempos de carga y recarga ultrarrápidos en desarrollo.*
* **Peticiones HTTP:** Axios / Supabase JS Client.
* **Estilos:** CSS/Tailwind CSS *(Ajustar según lo que decida el equipo)*.

---

## 📋 Requisitos Previos

Asegúrate de tener instalado en tu máquina lo siguiente:
* **Python 3.10+**
* **Node.js 18+** (Recomendado versión LTS)
* **Git**

---