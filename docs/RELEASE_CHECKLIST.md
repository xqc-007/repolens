# Release checklist

Use this before pushing a portfolio release.

- [ ] `backend/.env` exists locally but is not tracked
- [ ] `python -m pytest` passes
- [ ] `PYTHONPATH=backend python evals/run_evals.py` passes
- [ ] `npm run build` passes
- [ ] demo login diagnosis works
- [ ] proposed login patch is shown before execution
- [ ] tests require an explicit click
- [ ] GitHub repository picker loads selected repos
- [ ] private repo analysis works with read-only token access
- [ ] System page shows `github_write` disabled
- [ ] no `workspaces/`, SQLite DBs, `.venv`, `node_modules` or build output are tracked
- [ ] screenshots in `docs/screenshots/` show Home, Ask/result, Changes and System
