# Free OpenRouter models

Add `OPENROUTER_API_KEY` to the root `.env` and restart the backend. Lowercase
`openrouter_api_key` also works. With `LLM_PROVIDER=auto` (the default), a nonempty
key selects OpenRouter even if the old Ollama settings remain in `.env`.
The key stays in the backend; no frontend environment variable is needed.

| Work | Preferred free model | Reason for selection |
| --- | --- | --- |
| News event extraction, report writing | `google/gemma-4-26b-a4b-it:free` | Smaller active model for concise classification and prose |
| Advisor sector analysis | `google/gemma-4-31b-it:free` | Larger general instruction model for interpreting events |
| Company reasoning, strategy, portfolio advice | `nvidia/nemotron-3-super-120b-a12b:free` | Reasoning model for combining evidence and constraints |

These are task-based starting choices, not a financial accuracy benchmark.
Model availability and zero prompt/completion prices were checked against the
[live catalog](https://openrouter.ai/api/v1/models) on September 17, 2026.
Override the three preferences with `OPENROUTER_FAST_MODEL`,
`OPENROUTER_ANALYSIS_MODEL`, and `OPENROUTER_REASONING_MODEL`.

Requests try the preferred model, the analysis model when different, and finally
[`openrouter/free`](https://openrouter.ai/docs/guides/routing/routers/free-router).
That final router chooses among available free models; it does not preserve the
preferred model's specialization. During live checks, upstream limits required
fallbacks. The advisor's model attribution and server logs record the model that
actually answered.

Provider routing retains its default policy; speed does not override model
preferences. Connections are reused across requests and agents. Independent articles run in batches of three;
the shared runtime also caps upstream concurrency at three per backend worker.
The advisor retains its dependency order so later steps receive earlier results.

Identical zero-temperature requests share in-flight work and reuse a successful
response for five minutes, including its actual model attribution. Cache keys
include the full prompts, task, routing/options, and credential scope; changing
facts, holdings, model choices, or credentials causes a fresh request. The cache
stores at most 256 responses in memory, never on disk. Nonzero-temperature calls
remain independent. Set `OPENROUTER_CACHE_TTL_SECONDS=0` to disable reuse of
completed responses. Failures are never cached.

`OPENROUTER_TIMEOUT_SECONDS` defaults to 60 seconds and bounds the complete
call, including queueing and generation, rather than just socket inactivity.
At most 32 distinct calls may be pending per worker; excess work uses the existing
deterministic fallback. Server shutdown closes pooled connections and cancels
pending work. Output allowances retain the original budgets: 768 tokens for
extraction, 2048 for analysis and writing, and 6144 for complex reasoning.
Prompts and context are not shortened by the performance layer, and model
choices and reasoning settings are unchanged. Exact-input caching returns the
previous response verbatim, with the same model attribution.

These changes avoid reducing model capacity or output budgets to improve speed.
They are not a guarantee of equal predictive accuracy: the tests verify routing,
input/output preservation, caching, and failure handling. A representative,
labeled financial evaluation would be needed to measure answer accuracy.

The client rejects paid model IDs and sets provider maximum prompt, completion,
and per-request prices to zero. No paid search plugins or cloud embedding calls
are enabled. The backend sends each feature's prompt and supplied context to
OpenRouter when that feature runs.

Structured tasks request JSON; writing requests prose. Extraction and writing
disable reasoning when supported; deeper tasks request low reasoning effort
with a larger output allowance. Output sizes and request timeouts are bounded.
Empty, truncated, or malformed responses trigger the existing deterministic
fallbacks. API authentication/quota/service errors put requests into a short
shared cooldown, respecting numeric Retry-After values up to five minutes.

Free access has [account and provider limits](https://openrouter.ai/docs/api/reference/limits).
A multi-step report uses several calls, and article extraction uses a call per
article. Model fallback does not remove account limits. If free routes fail, the
app keeps working using deterministic rules. This is not unlimited hosted capacity.

Research uses the existing local `HashingEmbedder` in OpenRouter mode, keeping
ingestion and queries in one reproducible vector space without cloud costs.
This is lexical retrieval, not semantic embeddings. If your existing documents
used Ollama embeddings, re-ingest them for compatible retrieval. Predictions,
backtests, and portfolio calculations retain their numerical implementations.

Use `LLM_ENABLED=false` for deterministic operation, or `LLM_PROVIDER=compatible`
to select the existing `LLM_BASE_URL`, `LLM_MODEL`, and `ADVISOR_*_MODEL` settings.

To verify the key, routing, and first/repeat latency with synthetic data (up to
three free requests with caching enabled, no database writes, no key printed),
run from the repository root:

```powershell
.venv/Scripts/python.exe main/scripts/check_openrouter.py
```

The integration tests mock HTTP and require no API key:

```powershell
cd main
../.venv/Scripts/python.exe -m pytest backend/tests/test_openrouter.py -q
```
