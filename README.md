<p align="center">
  <h1 align="center">Vulhub-Web</h1>
  <p align="center">
    <strong>Web-based Vulnerability Lab Management Platform</strong>
    <br>
    Zero-config import · One-click lifecycle · Real-time monitoring
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/fastapi-0.115-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/docker-required-blue.svg" alt="Docker">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
</p>

---

## Overview

**Vulhub-Web** is a lightweight web platform for managing [Vulhub](https://github.com/vulhub/vulhub) vulnerability labs. It natively adapts to Vulhub's directory structure, providing automatic discovery, on-demand builds, one-click start/stop/destroy, and full lifecycle management — all through a clean web UI.

Designed for security researchers, penetration testers, and educators who need to spin up vulnerability environments quickly without manual Docker commands.

### Key Features

- **Zero-config Import** — Point to a Vulhub clone and auto-discover all vulnerability labs
- **One-click Lifecycle** — Build, start, stop, and destroy labs from the web UI
- **Real-time Logs** — SSE-powered streaming container logs
- **Web Terminal** — xterm.js + WebSocket for interactive shell access
- **Resource Monitoring** — Docker disk usage, image/container counts, per-container stats
- **Smart Scheduling** — Auto-scan for new labs, cache cleanup, idle lab reclamation
- **30+ Categories** — Auto-classification: log4j, shiro, fastjson, struts2, tomcat, weblogic, etc.
- **Dark Theme UI** — Responsive, Bootstrap 5-based single-page application

### Screenshots

| Dashboard | Lab Detail |
|:---:|:---:|
| Vulnerability library with category filtering | README rendering, logs, and terminal |

## Quick Start

### Prerequisites

- Python 3.9+
- Docker and Docker Compose (on the host)
- [Vulhub](https://github.com/vulhub/vulhub) — clone it to a directory of your choice
  ```bash
  git clone https://github.com/vulhub/vulhub.git /opt/vulhub
  ```

### Installation

```bash
# 1. Clone Vulhub (the vulnerability environments) — separate repo
git clone https://github.com/vulhub/vulhub.git ~/work/vulhub

# 2. Clone Vulhub-Web (the management platform) — sibling to vulhub
git clone https://github.com/Fuzzy-World/vulhub-web.git ~/work/Vulhub-Web
cd ~/work/Vulhub-Web

# 3. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the server
python run.py
```

Open `http://localhost:8088`, set admin password, then go to Settings and set **Vulhub Root Path** to `../vulhub` (relative path works since they're siblings).

### Docker Deployment

Vulhub-Web image does **not** include Vulhub itself. Use the sibling directory layout:

```
~/work/
├── vulhub/        ← git clone https://github.com/vulhub/vulhub
└── Vulhub-Web/    ← this repo
    └── docker-compose.yml
```

Then from inside `Vulhub-Web/`:

```bash
docker compose up -d
```

This mounts:
- `../vulhub` → `/vulhub` (read-only) inside the container
- `/var/run/docker.sock` → host Docker socket
- `./data` → SQLite persistence

Open `http://localhost:8088` and set **Vulhub Root Path** to `/vulhub` in Settings.
  -e VULHUB_ROOT_PATH=/vulhub \
  vulhub-web
```

## Architecture

```
┌─────────────────────────────────────────────┐
│                  Browser                     │
│  Bootstrap 5 + xterm.js + SSE               │
└──────────────────┬──────────────────────────┘
                   │ HTTP / WS / SSE
┌──────────────────▼──────────────────────────┐
│              FastAPI Server                  │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Routers  │  │ Services │  │ Scheduler  │  │
│  │ (API)    │──│ (Logic)  │  │ (Cron)     │  │
│  └─────────┘  └──────────┘  └────────────┘  │
│                     │                        │
│              ┌──────▼──────┐                 │
│              │   SQLite    │                 │
│              └─────────────┘                 │
└──────────────────┬──────────────────────────┘
                   │ Docker SDK / subprocess
┌──────────────────▼──────────────────────────┐
│             Docker Engine                    │
│  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │
│  │ Lab 1   │  │ Lab 2   │  │ Lab N ...   │  │
│  └─────────┘  └─────────┘  └─────────────┘  │
└─────────────────────────────────────────────┘
```

## Project Structure

```
vulhub-web/
├── app/                    # Application package
│   ├── main.py             # FastAPI entry point
│   ├── config.py           # Global configuration
│   ├── database.py         # SQLite setup & migrations
│   ├── models.py           # ORM models (Vuln, Task, Config, Container)
│   ├── routers/            # API route handlers
│   │   ├── auth.py         # POST /api/auth/*
│   │   ├── vulns.py        # GET/POST /api/vulns/*
│   │   ├── ranges.py       # POST/GET/WS /api/ranges/*
│   │   ├── docker.py       # GET/POST /api/docker/*
│   │   ├── settings.py     # GET/POST /api/settings/*
│   │   └── tasks.py        # GET /api/tasks/*
│   └── services/           # Business logic
│       ├── auth_service.py      # JWT + bcrypt
│       ├── vuln_service.py      # Vulhub scanning & parsing
│       ├── range_service.py     # Docker compose lifecycle
│       ├── docker_service.py    # Docker SDK wrapper
│       └── scheduler_service.py # APScheduler jobs
├── static/                 # Frontend SPA
│   ├── index.html
│   ├── css/app.css
│   └── js/*.js
├── data/                   # SQLite database (auto-created)
├── run.py                  # Entry point
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/auth/status` | Check if admin password is set |
| `POST` | `/api/auth/login` | Login with password |
| `POST` | `/api/auth/init` | Initialize admin password |
| `GET` | `/api/vulns` | List vulnerabilities (paginated, filterable) |
| `POST` | `/api/vulns/scan` | Trigger incremental Vulhub scan |
| `GET` | `/api/vulns/categories` | Get category list with counts |
| `GET` | `/api/vulns/{id}/readme` | Get rendered README |
| `POST` | `/api/ranges/{id}/build` | Build Docker images |
| `POST` | `/api/ranges/{id}/start` | Start lab containers |
| `POST` | `/api/ranges/{id}/destroy` | Destroy lab containers |
| `GET` | `/api/ranges/{id}/logs` | Stream container logs (SSE) |
| `WS` | `/api/ranges/{id}/terminal` | Web terminal (WebSocket) |
| `GET` | `/api/ranges/running` | List all running labs |
| `GET` | `/api/docker/info` | Docker resource info |
| `POST` | `/api/docker/cleanup` | Clean Docker resources |
| `GET` | `/api/settings` | Get system settings |
| `POST` | `/api/settings` | Update system settings |

## Configuration

All settings are managed through the web UI under **Settings**. Key options:

| Setting | Default | Description |
|---------|---------|-------------|
| Vulhub Root Path | (empty) | Path to Vulhub repository clone |
| Server Port | 8088 | HTTP server port |
| Idle Timeout | 0 (disabled) | Auto-destroy idle labs after N hours |
| Remove Images | true | Remove Docker images on destroy |
| Scan Cron | `0 */6 * * *` | Vulnerability scan schedule |
| Cleanup Cron | `0 2 * * *` | Docker cleanup schedule |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.9+, FastAPI, uvicorn |
| **Database** | SQLite + SQLAlchemy ORM |
| **Frontend** | Bootstrap 5, jQuery, xterm.js, marked.js |
| **Auth** | Custom JWT (HMAC-SHA256) + bcrypt |
| **Real-time** | SSE (logs), WebSocket (terminal) |
| **Scheduling** | APScheduler (BackgroundScheduler) |
| **Docker** | docker-py SDK + subprocess fallback |

## Security

- JWT authentication with 72-hour token expiry
- bcrypt password hashing (cost factor auto)
- Path traversal protection on README asset serving
- Port conflict detection before lab startup
- Admin-only access to all management endpoints

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License — see [LICENSE](LICENSE) for details.

## Acknowledgments

- [Vulhub](https://github.com/vulhub/vulhub) — The open-source vulnerability environment collection
- [FastAPI](https://fastapi.tiangolo.com/) — Modern Python web framework
- [xterm.js](https://xtermjs.org/) — Terminal frontend component
