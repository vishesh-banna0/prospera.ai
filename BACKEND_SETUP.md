# Backend Environment Setup

This project is currently being set up backend-first.

The frontend can be added later without changing this Python environment foundation.

## Files

- `requirements.txt`: runtime dependencies for the backend
- `requirements-dev.txt`: local development, linting, and testing tools
- `.env.example`: template for local environment variables

## Recommended Setup

0. Use Python 3.11

```powershell
python --version
```

Prospera backend setup should currently use Python 3.11.

Python 3.14 may fail during dependency installation because some packages in the backend stack,
especially `pydantic-core`, may not yet provide a compatible prebuilt wheel for that interpreter
in your environment.

1. Create a virtual environment

```powershell
py -3.11 -m venv .venv
```

2. Activate the virtual environment

```powershell
.venv\Scripts\Activate.ps1
```

3. Install runtime dependencies

```powershell
pip install -r requirements.txt
```

4. Install development dependencies

```powershell
pip install -r requirements-dev.txt
```

5. Create a local environment file

```powershell
Copy-Item .env.example .env
```

6. Update the values in `.env` for your local machine

## Notes

- `requirements.txt` is intentionally backend-focused.
- Frontend dependencies should be added later in their own frontend workspace.
- Each backend module ships its own raw SQL migration under `backend/modules/<module>/infrastructure/migrations/`; apply them to PostgreSQL in date order. Docker files and CI setup are still pending.
- If you already created `.venv` using Python 3.14, delete that virtual environment and recreate it with Python 3.11.
