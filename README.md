# S1 - Customer & Account Management (LabBank)

Service S1 (ACC1-S) of the LabBank project: customers, login with JWT, user profiles and bank accounts with Sheba numbers.
Python 3.12, FastAPI, PostgreSQL. The API contract is `openapi/account.yaml`.

## Quick start (Docker)
```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # put the result in .env as JWT_SECRET
docker compose up --build
```

| What | URL |
| --- | --- |
| Service (API) | http://localhost:8081 |
| Swagger UI | http://localhost:8081/docs |
| Frontend (nginx) | http://localhost:8080 |
| PostgreSQL (from your machine only) | 127.0.0.1:5432 |

`compose.yaml` also starts a stub of S2 (Prism, made from `docs/s2-account-created.openapi.yaml`), so S1 runs alone; `.env.example` has a development-only `JWT_SECRET`, so `cp .env.example .env` is enough. Use your own random secret outside development.

`docker compose down` keeps the data (volume `s1_pgdata`). `docker compose down -v` deletes it.

## Demo data
With `SEED_DATA=1` (the Compose default) the service creates this data at start; running it again does nothing new.

| Kind | National code / id | Notes |
| --- | --- | --- |
| User | `3740681241` | password `Str0ng-pass1` |
| User | `6907366258` | password `Str0ng-pass1` |
| ACTIVE account | `0192a7e4-6b1d-7c3e-9a41-2f5d8e0b7c11` | Sheba `IR740990000000000000000001` |
| BLOCKED account | `0192a7e5-1c2d-7a90-8b33-4d6e9f0a1b22` | Sheba `IR470990000000000000000002` |

Roles (`USER`, `ADMIN`, `MANAGER`, `OFFICER`) are set in the database, for example:
```bash
docker compose exec db psql -U labbank -d s1_accounts -c "update users set role = 'ADMIN' where national_code = '3740681241';"
```

## Run without Docker
```bash
docker compose up -d db
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
JWT_SECRET=<a-random-value-of-16-or-more-characters> python -m uvicorn main:app --port 8081
```
The default `DATABASE_URL` matches `.env.example`.

## Frontend
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, forwards /api, /health and /ready to port 8081
npm run gen:api    # regenerate src/api/schema.d.ts after the contract changed
```

## Tests
```bash
pip install -r requirements-dev.txt
pytest                                                      # all tests
pytest tests/test_login.py::test_login_success_returns_jwt -v   # one test
```
Most tests use a temporary SQLite database, so PostgreSQL is not needed.

```bash
pytest --cov --cov-report=term-missing   # coverage of app/ (line and branch, see .coveragerc)
pytest -m postgres                       # only the tests on a real PostgreSQL (Testcontainers, Docker must run)
pytest -m "not postgres"                 # everything else
```
The PostgreSQL tests start `postgres:16-alpine` and are skipped when Docker is not available.
`tests/test_contract_conformance.py` checks the answers of the API against `openapi/account.yaml`.
API requests for Bruno are in `tests-api/` (open the folder in Bruno, choose the `local` environment, Run Collection).

## Configuration
| Variable | Default | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | local PostgreSQL | database connection |
| `JWT_SECRET` | dev value in `.env.example` | signing key, at least 16 characters (use your own outside development) |
| `ACCESS_TOKEN_MINUTES` / `REFRESH_TOKEN_DAYS` | 15 / 7 | token lifetimes |
| `MAX_FAILED_LOGIN_ATTEMPTS` / `LOGIN_LOCK_MINUTES` | 5 / 15 | login lock |
| `MAX_ACCOUNTS_PER_USER` | 5 | accounts one user may have |
| `BCRYPT_ROUNDS` | 12 | password hashing cost |
| `CORS_ORIGINS` | the Vite dev server | allowed browser origins |
| `SEED_DATA` | 1 in Compose | create the demo data |
| `S2_BASE_URL` | `http://s2:8082` (the stub) in Compose | address of S2; empty means S2 is not told about new accounts |
| `LOG_LEVEL` | INFO | log level |
| `S1_PORT`, `FRONTEND_PORT`, `DB_HOST_PORT` | 8081, 8080, 5432 | published ports (Compose only) |

## CI and releases
- `.github/workflows/ci.yml` runs on every pull request: `backend` (ruff, tests on SQLite and a real PostgreSQL, coverage, image build), `frontend` (eslint, build, generated api types up to date) and `contract` (redocly lint).
- Before a pull request: `ruff check . && ruff format --check . && pytest`.
- Release: change `version` in `main.py`, merge, then `git tag v0.8.0 && git push origin v0.8.0`. `.github/workflows/release.yml` builds the image once and pushes `ghcr.io/<owner>/labbank-account:0.8.0` and `:sha-<short sha>`; the digest is in the run summary. Make the package public in GitHub (Packages, Package settings).