# serene-backend — file index

Generated: 2026-03-29. This file catalogs the repository; it does not modify any other project files.

## Summary

| Scope | Notes |
|-------|--------|
| Listed paths | Application source, config, data, and DB; Python bytecode under `__pycache__/` is omitted from the list below but left on disk. |
| Runtime / local | `local_data/session/*.json` and `serene.db` are local/runtime artifacts. |

## File listing (excluding `__pycache__/` and `*.pyc`)

```
.env
.env.example
.gitignore
app/__init__.py
app/core/__init__.py
app/core/config.py
app/core/database.py
app/endpoints/__init__.py
app/endpoints/admin.py
app/endpoints/chat.py
app/endpoints/completions.py
app/endpoints/daily.py
app/endpoints/tasks.py
app/endpoints/user.py
app/models/__init__.py
app/models/db_models.py
app/models/schemas.py
app/service/__init__.py
app/service/analysis_service.py
app/service/daily_service.py
app/service/oracle_service.py
app/service/session_file_service.py
app/service/task_service.py
app/service/user_service.py
app/utils/__init__.py
app/utils/oracle_prompt.py
app/utils/time_utils.py
local_data/session/incri_20260329_023656_4210f797.json
local_data/session/incri_20260329_023656_7fcaec4b.json
local_data/session/incri_20260329_024209_5692d3e9.json
local_data/session/incri_20260329_024223_0371872e.json
local_data/session/incri_20260329_024223_1799f3a0.json
local_data/session/incri_20260329_024656_898f6e96.json
local_data/session/incri_20260329_025417_65d78038.json
local_data/session/incri_20260329_025417_fd414b18.json
local_data/session/incri_20260329_025856_df9ef818.json
local_data/session/incri_20260329_025856_fe7d6273.json
local_data/session/incri_20260329_025904_c230f694.json
local_data/session/incri_20260329_025904_c85e17cf.json
local_data/session/incri_20260329_030006_1d546c3a.json
local_data/session/incri_20260329_030006_71bbc8cf.json
local_data/session/incri_20260329_030432_8ee86885.json
local_data/session/incri_20260329_030432_e7c5931a.json
local_data/session/incri_20260329_030519_b3880260.json
local_data/session/incri_20260329_030519_dff1290d.json
local_data/session/incri_20260329_030615_a7b4e07a.json
local_data/session/incri_20260329_030615_f308d57b.json
local_data/session/incri_20260329_030858_5b3ea489.json
local_data/session/incri_20260329_030918_7da94466.json
local_data/session/incri_20260329_031314_833f6c35.json
local_data/session/incri_20260329_031314_c310bdbd.json
local_data/session/incri_20260329_031839_66fd22a1.json
local_data/session/incri_20260329_031839_f3a9d0e4.json
local_data/session/incri_20260329_031848_52b273ee.json
local_data/session/incri_20260329_031848_5ccc4b1b.json
main.py
README.md
requirements.txt
serene.db
```

## Layout

- `app/core/` — configuration and database setup.
- `app/endpoints/` — API route handlers.
- `app/models/` — DB models and Pydantic schemas.
- `app/service/` — business logic.
- `app/utils/` — helpers (prompts, time).
- `local_data/session/` — session JSON files.
- Bytecode caches live under `app/**/__pycache__/` when the app runs; those files were not altered.
