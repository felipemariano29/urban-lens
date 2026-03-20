# 🗄️ Database Initialization Guide

This project uses PostgreSQL with automatic initialization scripts to bootstrap the database during the first startup.

---

## 📁 Initialization Directory

All database scripts must be placed inside the following folder at the root of the project:

```bash
assets/postgres/
```

### Example Structure

```bash
.
├── docker-compose.yml
├── assets
│   └── postgres
│       ├── 0000.sql
│       ├── 0010.sql
│       ├── 0020.sql
│       └── 0030.sql
└── README.md
```

---

## ⚙️ How It Works

PostgreSQL automatically executes all scripts located in:

```
/docker-entrypoint-initdb.d
```

In this project, `assets/postgres/` is mounted into that directory.

✅ Supported file types:
- `.sql`
- `.sh`
- `.sql.gz`

📌 Scripts are executed in **alphabetical order**.

---

## 🔢 Naming Convention

All scripts must follow this pattern:

```bash
0000.sql
0010.sql
0020.sql
0030.sql
```

### Rules

- Always use **4 digits**
- Always increment by **10**
- Never rename existing files
- Leave gaps for future inserts

### Why increment by 10?

This allows inserting new scripts later:

```bash
0015.sql   # inserted between 0010 and 0020
```

---

## 🧩 Script Organization

Suggested structure:

| File       | Purpose              |
|------------|---------------------|
| 0000.sql   | bootstrap (schemas) |
| 0010.sql   | core tables         |
| 0020.sql   | indexes             |
| 0030.sql   | seed data           |

---

## 🧪 Example Scripts

### 0000.sql

```sql
CREATE SCHEMA IF NOT EXISTS core;
```

### 0010.sql

```sql
CREATE TABLE IF NOT EXISTS core.sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 0020.sql

```sql
INSERT INTO core.sources (name)
VALUES ('DATA.POLICE.UK')
ON CONFLICT DO NOTHING;
```

---

## 🚀 How to Populate the Database

1. Add your scripts to `assets/postgres/`
2. Follow the naming convention
3. Start the environment:

```bash
docker compose up -d
```

or:

```bash
make up
```

✅ PostgreSQL will automatically execute all scripts on first startup.

---

## ⚠️ Important Behavior

Initialization scripts run **only once**, when the database is created.

If the database already exists:

❌ Scripts will NOT run again

---

## 🔄 Re-running Scripts

To force execution again:

```bash
docker compose down -v
docker compose up -d
```

or:

```bash
make reset
```

> ⚠️ Warning: This will delete all existing database data.

---

## 💡 Best Practices

- Keep scripts **small and focused**
- Separate **schema**, **tables**, and **seed data**
- Use `IF NOT EXISTS` whenever possible
- Avoid large monolithic SQL files
- Maintain consistent numbering

---

## ✅ Summary

- Use `assets/postgres/` folder
- Name scripts as `0000.sql`, `0010.sql`, etc.
- Increment by 10
- Scripts run automatically on first startup
- Reset the volume to re-run them

---

## 🧠 Tip

Think of these scripts as your **initial database blueprint**.  
For future evolution, consider adding a proper migration tool.
