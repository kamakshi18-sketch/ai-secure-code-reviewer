# AI Secure Code Reviewer - Agent Instructions

This document provides guidance for AI agents working on this codebase.

## Project Overview

AI Secure Code Reviewer is a production-quality platform that automates security code reviews using deterministic static analysis tools and AI-powered reasoning. The system integrates multiple security scanners, uses RAG for accurate security recommendations, generates minimal secure patches, verifies fixes through automated testing, and creates professional GitHub Pull Requests.

## Architecture Principles

1. **Modular Microservice-Inspired Design** - Separate modules for each concern
2. **Clean Architecture** - Dependency inversion, separation of concerns
3. **Async First** - All I/O operations are asynchronous
4. **Type Safety** - Full type hints, Pydantic models, TypeScript
5. **Security by Default** - No secrets in code, RBAC, input validation
6. **Observability** - Structured logging, metrics, tracing

## Key Components

### Backend (FastAPI + Celery + PostgreSQL + Redis + ChromaDB)

```
backend/
├── api/v1/endpoints/       # REST endpoints organized by resource
├── agents/                 # Specialized AI agents
│   ├── base.py            # BaseAgent with LLM integration
│   ├── coordinator.py     # Orchestrates multi-agent workflows
│   ├── security_analysis.py  # Vulnerability analysis
│   └── patch_generator.py    # Secure patch generation
├── core/
│   ├── config.py          # Pydantic Settings management
│   ├── security.py        # JWT auth, password hashing, RBAC
│   ├── celery_app.py      # Celery configuration
│   └── logging.py         # Structured logging with structlog
├── database/
│   ├── session.py         # Async SQLAlchemy session
│   └── init/              # Database initialization scripts
├── models/                # SQLAlchemy ORM models
├── schemas/               # Pydantic request/response models
├── tasks/                 # Celery background tasks
│   ├── repository_tasks.py
│   ├── scan_tasks.py
│   ├── patch_tasks.py
│   ├── verification_tasks.py
│   ├── report_tasks.py
│   ├── github_tasks.py
│   └── maintenance_tasks.py
├── github/                # GitHub API integration
├── rag/                   # Retrieval-Augmented Generation
│   └── engine.py          # ChromaDB + sentence-transformers
├── security/              # Security scanner wrappers
│   └── scanners.py        # Semgrep, Bandit, Gitleaks, Trivy, etc.
├── verification/          # Patch verification service
└── utils/                 # Shared utilities
```

### Frontend (React + TypeScript + Vite + Tailwind)

```
frontend/
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── ui/           # Base components (Button, Input, Card, etc.)
│   │   └── Layout.tsx    # Main layout with sidebar
│   ├── pages/            # Page components
│   ├── services/api.ts   # Axios API client
│   ├── contexts/         # React contexts (Auth)
│   ├── hooks/            # Custom React hooks
│   ├── store/            # Zustand state management
│   ├── types/            # TypeScript interfaces
│   └── utils/            # Utility functions
```

## Development Workflow

### Adding a New API Endpoint

1. Define Pydantic schemas in `backend/schemas/__init__.py`
2. Add database model if needed in `backend/models/__init__.py`
3. Create endpoint in `backend/api/v1/endpoints/<resource>.py`
4. Register in `backend/api/v1/router.py`
5. Add TypeScript types in `frontend/src/types/index.ts`
6. Add API function in `frontend/src/services/api.ts`
7. Create UI components as needed

### Adding a New Security Scanner

1. Create scanner class in `backend/security/scanners.py` extending `BaseScanner`
2. Implement `scan()` method returning `List[Finding]`
3. Add to `ScannerManager.get_available_scanners()`
4. Update scan task to use new scanner
5. Add scanner configuration to settings

### Adding a New AI Agent

1. Extend `BaseAgent` in `backend/agents/base.py`
2. Implement `process()` method
3. Register in `CoordinatorAgent` if needed
3. Add RAG queries for domain knowledge
4. Ensure prompts follow security guidelines (no hallucination)

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Code Standards

### Python (Backend)
- **Formatter**: Black (line length 100)
- **Import Sorter**: isort
- **Linter**: Ruff
- **Type Checker**: mypy (strict mode)
- **Test Framework**: pytest + pytest-asyncio
- **Async**: Use `async/await` throughout, no blocking calls in async functions

### TypeScript (Frontend)
- **Formatter**: Prettier + Tailwind CSS plugin
- **Linter**: ESLint with React hooks plugin
- **Type Checker**: tsc (strict mode)
- **Test Framework**: Vitest + React Testing Library
- **State**: Zustand for global state, React Query for server state

### Git Conventions
- **Branches**: `feature/`, `fix/`, `refactor/`, `docs/`, `chore/`
- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, etc.)
- **PRs**: Require CI pass, code review, updated docs

## Security Guidelines

1. **Never commit secrets** - Use environment variables
2. **Validate all inputs** - Pydantic models for API, Zod for frontend
3. **Use parameterized queries** - SQLAlchemy ORM prevents SQL injection
4. **Implement RBAC** - Check permissions on every endpoint
5. **Rate limiting** - Apply to all public endpoints
6. **Audit logging** - Log all security-relevant actions
7. **Dependency scanning** - Automated in CI/CD

## Testing Strategy

### Unit Tests
- Test individual functions/classes in isolation
- Mock external dependencies (API calls, DB, LLM)
- Target: >80% coverage

### Integration Tests
- Test API endpoints with test database
- Test Celery tasks with test broker
- Test scanner integration

### E2E Tests
- Critical user flows (login, scan, patch, PR)
- Use Playwright for browser automation

## Deployment Checklist

- [ ] All environment variables set
- [ ] Database migrations applied
- [ ] SSL certificates configured
- [ ] Secrets rotated from defaults
- [ ] Monitoring alerts configured
- [ ] Backup strategy implemented
- [ ] Load testing completed
- [ ] Security scan passed

## Common Commands

```bash
# Start development stack
docker-compose up -d

# View logs
docker-compose logs -f backend

# Run backend tests
docker-compose exec backend pytest

# Run frontend tests
docker-compose exec frontend npm run test

# Database shell
docker-compose exec postgres psql -U ai_reviewer -d ai_code_reviewer

# Redis CLI
docker-compose exec redis redis-cli

# ChromaDB check
curl http://localhost:8001/api/v1/heartbeat

# Celery monitor
docker-compose exec celery-worker celery -A core.celery_app inspect active

# Rebuild after dependency changes
docker-compose build backend frontend
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Database connection failed | Check `DATABASE_URL`, ensure Postgres is healthy |
| Redis connection failed | Check `REDIS_URL`, ensure Redis is healthy |
| Scanner not found | Install scanner in Dockerfile, check PATH |
| LLM API error | Verify API keys, check rate limits |
| Celery tasks stuck | Check broker connection, task timeouts |
| Frontend build fails | Clear node_modules, reinstall |

### Debugging Tips

1. **Enable debug logging**: Set `LOG_LEVEL=DEBUG` in .env
2. **Check Celery tasks**: `celery -A core.celery_app inspect active`
3. **Database queries**: Enable SQLAlchemy echo in development
4. **API requests**: Check browser DevTools Network tab
5. **Container logs**: `docker-compose logs -f <service>`

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [React Query Docs](https://tanstack.com/query/latest)
- [Zustand Docs](https://github.com/pmndrs/zustand)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [ChromaDB Docs](https://docs.trychroma.com/)
- [LangChain Docs](https://python.langchain.com/)