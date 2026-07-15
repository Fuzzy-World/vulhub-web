# Contributing to Vulhub-Web

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/vulhub-web.git
cd vulhub-web

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python run.py
```

## Project Structure

```
vulhub-web/
├── app/                    # Application package
│   ├── __init__.py
│   ├── main.py             # FastAPI app entry point
│   ├── config.py           # Global configuration
│   ├── database.py         # SQLite database setup
│   ├── models.py           # SQLAlchemy ORM models
│   ├── routers/            # API route handlers
│   │   ├── auth.py         # Authentication endpoints
│   │   ├── vulns.py        # Vulnerability library endpoints
│   │   ├── ranges.py       # Lab management endpoints
│   │   ├── docker.py       # Docker monitoring endpoints
│   │   ├── settings.py     # System settings endpoints
│   │   └── tasks.py        # Task history endpoints
│   └── services/           # Business logic layer
│       ├── auth_service.py
│       ├── vuln_service.py
│       ├── range_service.py
│       ├── docker_service.py
│       └── scheduler_service.py
├── static/                 # Frontend assets (SPA)
│   ├── index.html
│   ├── css/
│   └── js/
├── data/                   # Runtime data (SQLite DB)
├── run.py                  # Application entry point
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Pull Request Guidelines

1. Fork the repository and create a feature branch
2. Follow the existing code style and conventions
3. Add tests for new functionality where applicable
4. Update documentation if needed
5. Ensure all existing functionality still works

## Code Style

- Python: PEP 8 with 4-space indentation
- JavaScript: ES6+ with 2-space indentation
- Comments and documentation in English
- Keep functions focused and single-purpose

## Questions?

Open an issue for bugs, feature requests, or questions.
