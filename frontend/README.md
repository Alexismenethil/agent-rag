# Frontend — Next.js (App Router)

UI del agente: subida de PDF con estado de ingesta, chat con selector de modo (estricto/ampliado),
visor que **resalta la cita** en el documento, historial y perfil. V0 solo muestra el estado del backend.

## Estructura

```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx        # V0: estado del backend (/health)
│   └── globals.css
├── lib/
│   └── api.ts          # cliente HTTP (API_URL); en V1+ tipos generados desde OpenAPI
├── next.config.mjs
└── tsconfig.json
```

> Pendiente por versión (ver docs/PLAN.md):
> V1 `app/documentos/` (subida + estado) y `app/chat/` con visor PDF y citas clicables (resaltado por
> página + snippet); `lib/api/types.gen.ts` generado con `make openapi`. V3 UX de voz. V4 perfil.

## Desarrollo

Con Docker (recomendado): desde la raíz `make up` (queda en http://localhost:3000).

Local sin Docker:
```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```
