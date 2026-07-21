# Prospera — web

The frontend for Prospera. A dark instrument console over the existing FastAPI
backend. See [`DESIGN.md`](DESIGN.md) for the visual system and the reasoning
behind it, and [`QUESTIONS.md`](QUESTIONS.md) for open backend gaps.

## Run it

```bash
# 1. backend (from the repo root, in another terminal) — see docs/FRONTEND_BRIEF.md §8
cd main && python main.py --reload      # → http://127.0.0.1:8000

# 2. frontend (from web/)
cp .env.example .env.local               # sets NEXT_PUBLIC_API_BASE_URL
npm install
npm run dev                              # → http://localhost:3000
```

Then open **http://localhost:3000/styleguide** — the design direction lives
there. The frontend talks to the backend directly (CORS is open); no proxy.

## Scripts

| Command | What it does |
|---------|--------------|
| `npm run dev` | Dev server with hot reload |
| `npm run build` | Production build |
| `npm run typecheck` | `tsc --noEmit` (strict) |
| `npm run lint` | ESLint |
| `npm run gen:api` | Regenerate the typed API client from `../main/openapi.json` |

## How it's laid out

```
src/
├── api/          client.ts (one fetch surface) · schema.ts (generated) · types.ts (aliases)
├── lib/          money.ts (all number/₹ formatting) · cn.ts · useHealth.ts
├── components/
│   ├── shell/    the instrument frame: status strip, side rail
│   ├── ui/       Gauge (signature), SignedNumber, Badge, Button, Input, Panel, Skeleton, States, icons
│   └── charts/   EquityCurve
└── app/          layout (fonts + providers) · styleguide · page · not-found
```

## Rules that keep it consistent

- **All money and numbers go through `src/lib/money.ts`.** No ad-hoc `toFixed`.
- **Colors come from tokens** (`bg-panel`, `text-up`, …), never raw hex. Tokens
  live in `src/app/globals.css`; names in `tailwind.config.ts`.
- **Never edit `src/api/schema.ts`** — regenerate with `npm run gen:api`.
- **The backend's error `detail` is shown verbatim** through `ErrorState`.
