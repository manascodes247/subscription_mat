Migration files record every change to Brightloop's database structure.

Apply all migrations before starting the API:

```powershell
alembic upgrade head
```

Create a new migration after changing SQLAlchemy models:

```powershell
alembic revision --autogenerate -m "describe the change"
```
