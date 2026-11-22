# Preparación de hosting para el Midterm

Esta configuración no crea servicios ni autoriza publicación. Crear y conectar servicios queda pendiente de autorización específica. La creación inicial de un servicio o proyecto conectado puede iniciar un despliegue incluso si se desactivan los despliegues automáticos posteriores.

## Cloudflare Pages Free

- Directorio raíz: `frontend`.
- Comando de build: `npm run build`.
- Directorio de salida: `dist`.
- Node.js: `24.19.0`, fijado en `frontend/.node-version`.
- Variables de build: `VITE_API_URL`, `VITE_SUPABASE_URL` y `VITE_SUPABASE_PUBLISHABLE_KEY`.
- Para ejecución local, la plantilla del frontend es `.env.example` en la raíz: Vite lee los archivos `.env` desde ese directorio. En Pages se usan variables del dashboard.
- El directorio no contiene `404.html` de nivel superior: Pages usa el fallback SPA para rutas de React Router.
- Al configurar el proyecto, desactivar los despliegues automáticos de la rama de producción y elegir `None` para previews. Verificar también que no haya una primera publicación antes de autorizar la creación. Una URL de preview distinta requiere añadir su origen explícito a CORS.

## Render Free

El Blueprint `render.yaml` define un Web Service gratuito, Python 3.11.18, directorio `backend`, build `pip install -r requirements.txt`, arranque `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health check `/health` y `autoDeployTrigger: 'off'`. El health check verifica que el proceso responde; no comprueba PostgreSQL ni Supabase Auth. Desactivar autodeploy no impide necesariamente el primer despliegue al crear el servicio. Si se utiliza Blueprint, desactivar también Auto Sync en sus ajustes.

Ingresar `DATABASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` y `CORS_ORIGINS` únicamente en la configuración privada del servicio; no compartir ni guardar sus valores en Git. `CORS_ORIGINS` acepta orígenes HTTP(S) explícitos separados por comas, sin rutas ni comodines. Usar la URL HTTPS exacta de Pages, sin barra final; localhost:5173 y 127.0.0.1:5173 permanecen habilitados.

Para PostgreSQL, usar la conexión **session pooler** de Supabase si se necesita IPv4, con TLS y un usuario de privilegios mínimos aprobado por el equipo. No agregar un IPv4 de pago ni cambiar políticas o permisos automáticamente. El pooler y la autorización deben verificarse sin conectarse a datos reales durante esta preparación. La conexión directa gratuita puede requerir IPv6.

Antes de publicar, resolver el riesgo de privilegios de Supabase previamente identificado, verificar el rol efectivo y la autorización, integrar las historias pendientes y obtener la autorización de publicación. Render Free puede suspender el proceso por inactividad y tiene límites de uso; sin método de pago puede suspender servicios al agotar cuotas. Confirmar que la cuenta no tenga cobros habilitados y no seleccionar recursos o planes de pago.

Fuentes: https://developers.cloudflare.com/pages/configuration/serving-pages/ ; https://developers.cloudflare.com/pages/configuration/branch-build-controls/ ; https://render.com/docs/free ; https://render.com/docs/blueprint-spec ; https://supabase.com/docs/guides/database/connecting-to-postgres
