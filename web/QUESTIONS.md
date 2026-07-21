# Open questions for the backend owner

Log for real gaps found while building the frontend. These don't block the
current work — each has a client-side workaround noted — but they'd simplify the
UI if added. (Do not patch the backend to resolve these; that's the owner's call.)

| # | Gap | Where it bites | Current workaround |
|---|-----|----------------|--------------------|
| 1 | No `GET /environments` (list) — only fetch-by-id | Portfolio Center can't show "your portfolios" | Persist created environment IDs in `localStorage`; design a real "no portfolios yet" first-run state |
| 2 | No single "analyze everything for this symbol" endpoint | The Analyze flow must call four `POST`s in order (score → predict → fuse → reason) | Orchestrate the four calls client-side and choreograph the reveal; an aggregate endpoint would remove the round-trips |
| 3 | Auth / multi-user not present | Whether to build any account UI now | Assume a single local user; no login built (brief §5) |

Both #1 and #2 are pre-flagged in `docs/FRONTEND_BRIEF.md` as small backend adds. Raise
if/when you want them.
