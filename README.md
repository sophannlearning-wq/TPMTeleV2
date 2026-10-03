# TPM Master Training Bot

Telegram training management system for Admin, Supervisor, and Staff roles.

## Admin menu
- Training Dashboard
- Score Update
- Generate Training Plan
- Create, edit, and cancel schedules
- Automatic and manual reminders
- Attendance
- Follow-up Training
- Reports
- Staff Management
- Lesson Management
- Telegram Linking
- Personal Staff View

## Deploy to Railway
1. Upload all repository files to a private GitHub repository.
2. Create a Railway project from the repository.
3. Add PostgreSQL.
4. Add variables: `BOT_TOKEN`, a reference to PostgreSQL `DATABASE_URL`, `TIMEZONE=Asia/Phnom_Penh`, and `DATA_DIR=data`.
5. Keep only one running bot service for the token.
6. Railway starts `python -m app.main` through the Dockerfile.
7. Send `/health`, then `/start` and enter Staff ID `90024252`.

## Excel formats
Score upload: `ID | Score`.
Attendance upload: `ID | Attendance | Remark`.

## Data
Replace the bootstrap Staff Master and optional history files in `data/` with approved organization files before production rollout. Do not commit secrets.
