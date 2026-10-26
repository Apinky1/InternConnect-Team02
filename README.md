# InternConnect — Team02

Cloud-based internship and career-readiness web application. **Prototype v0.1** includes an application tracker with add, change status, delete, and summary counts. Other features are planned, not implemented.

## Run locally (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 in your browser. If `py` is not available, try `python -m venv .venv`. If activation is blocked, run `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.\.venv\Scripts\python.exe app.py` without activating.

## Run tests

```powershell
python -m pytest -q
```

## Docker (optional after local verification)

```powershell
docker build -t internconnect .
docker run --rm -p 5000:5000 internconnect
```

**Note:** The prototype currently saves data in a local SQLite file. Cloud hosts may use ephemeral storage, so persistence must be addressed before production deployment. This starter does not include accounts/login, resume uploads, AI features, or production security protections. Do not upload private resumes or personal information during testing.

## Proposed roles (confirm with team)

- Aliyah: project coordination and frontend
- Makeda: backend and database
- Taylor: testing, deployment, and documentation plus an application feature
- Everyone: tests, meaningful GitHub commits, report and presentation

## Planned modules

- Interview and deadline tracking
- Career-readiness checklist
- Progress dashboard improvements

See `docs/next-steps.md`.
