# AI Secure Code Reviewer

> **Automatically detect security vulnerabilities, explain them using AI, generate secure fixes, verify the fixes, and create GitHub Pull Requests.**

[![CI/CD](https://github.com/your-org/ai-secure-code-reviewer/workflows/CI/CD/badge.svg)](https://github.com/your-org/ai-secure-code-reviewer/actions)
[![Security Scan](https://github.com/your-org/ai-secure-code-reviewer/workflows/Security/badge.svg)](https://github.com/your-org/ai-secure-code-reviewer/actions)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Overview

AI Secure Code Reviewer is a production-quality platform that automates security code reviews using a combination of deterministic static analysis tools and AI-powered reasoning. The system integrates multiple security scanners, uses Retrieval-Augmented Generation (RAG) for accurate security recommendations, generates minimal secure patches, verifies fixes through automated testing, and creates professional GitHub Pull Requests.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI Secure Code Reviewer                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  GitHub Repository ──► Repository Service ──► Language Detection           │
│                                                      │                       │
│                                                      ▼                       │
│                    ┌─────────────────────────────────────────────────┐     │
│                    │         Static Analysis Pipeline                 │     │
│                    │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │     │
│                    │  │Semgrep │ │ Bandit │ │Gitleaks│ │ Trivy  │    │     │
│                    │  └────────┘ └────────┘ └────────┘ └────────┘    │     │
│                    │  ┌────────┐ ┌────────┐                          │     │
│                    │  │pip-audit│ │npm audit│                         │     │
│                    │  └────────┘ └────────┘                          │     │
│                    └─────────────────────────────────────────────────┘     │
│                                      │                                     │
│                                      ▼                                     │
│                    ┌─────────────────────────────────────────────────┐     │
│                    │              AI Orchestrator                     │     │
│                    │  ┌──────────────┐ ┌──────────────┐              │     │
│                    │  │Security Agent │ │   RAG Agent  │              │     │
│                    │  └──────────────┘ └──────────────┘              │     │
│                    │  ┌──────────────┐ ┌──────────────┐              │     │
│                    │  │ Patch Agent  │ │ Verification │              │     │
│                    │  └──────────────┘ └──────────────┘              │     │
│                    └─────────────────────────────────────────────────┘     │
│                                      │                                     │
│                    ┌─────────────────┼─────────────────┐                  │
│                    ▼                 ▼                 ▼                  │
│            ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│            │  Test Runner │   │Security Re-Scan│   │  PR Creator │          │
│            └─────────────┘   └─────────────┘   └─────────────┘          │
│                    │                 │                 │                  │
│                    └─────────────────┼─────────────────┘                  │
│                                      ▼                                     │
│                    ┌─────────────────────────────────────────────────┐     │
│                    │              Report Generator                    │     │
│                    │  Markdown │ PDF │ JSON │ HTML                    │     │
│                    └─────────────────────────────────────────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Features

### Security Scanners
- **Semgrep** - Multi-language SAST with 3000+ rules
- **Bandit** - Python-specific security linter
- **Gitleaks** - Secret detection in git history
- **Trivy** - Vulnerability scanner for dependencies and containers
- **pip-audit** - Python dependency vulnerability scanning
- **npm audit** - JavaScript/TypeScript dependency scanning

### Supported Vulnerability Types
- SQL Injection (CWE-89)
- Cross-Site Scripting - XSS (CWE-79)
- Command Injection (CWE-78)
- Path Traversal (CWE-22)
- Hardcoded Secrets (CWE-798)
- SSRF (CWE-918)
- Insecure Deserialization (CWE-502)
- Broken Access Control
- Authentication/Authorization Issues
- Weak Cryptography
- Dependency Vulnerabilities
- And more...

### AI Capabilities
- **Root Cause Analysis** - Explains why vulnerabilities exist
- **Severity Assessment** - Justifies risk ratings with evidence
- **Secure Patch Generation** - Creates minimal, style-consistent fixes
- **RAG-Powered Recommendations** - Grounded in OWASP, CWE, CERT standards
- **Interactive Chat Assistant** - Answers security questions with citations

### Verification Pipeline
1. Apply generated patch
2. Run project test suite
3. Re-run security scanners
4. Compare findings (before vs after)
5. Auto-retry on failure (configurable)

### Reporting
- Executive Summary
- Security Score (0-100)
- Risk Score (0-100)
- Severity Distribution
- OWASP Top 10 Mapping
- CWE Mapping
- Before/After Comparison
- Patch Summary
- Export: Markdown, PDF, JSON, HTML

## Quick Start

### Prerequisites
- Docker 24+
- Docker Compose 2+
- GitHub Personal Access Token (for private repos)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/ai-secure-code-reviewer.git
cd ai-secure-code-reviewer

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Required: SECRET_KEY, OPENAI_API_KEY or ANTHROPIC_API_KEY, GITHUB_TOKEN
nano .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | JWT signing key (min 32 chars) | Yes |
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 | Yes* |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude | Yes* |
| `GITHUB_CLIENT_ID` | GitHub OAuth App ID | For auth |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth Secret | For auth |
| `GITHUB_WEBHOOK_SECRET` | Webhook signature verification | For webhooks |
| `POSTGRES_PASSWORD` | Database password | Yes |
| `REDIS_URL` | Redis connection string | Yes |

*At least one LLM provider required

### Scanner Configuration

```env
# Semgrep config: auto, p/ci, p/security-audit, p/secrets
SEMGREP_CONFIG=auto

# Trivy severity levels
TRIVY_SEVERITY=HIGH,CRITICAL

# Scan timeout (seconds)
SCAN_TIMEOUT=1800

# Max patch regeneration attempts
MAX_PATCH_RETRIES=3
```

## API Reference

### Authentication
```
POST   /api/v1/auth/login          # Login
POST   /api/v1/auth/register       # Register
POST   /api/v1/auth/refresh        # Refresh token
POST   /api/v1/auth/logout         # Logout
GET    /api/v1/auth/me             # Current user
```

### Repositories
```
GET    /api/v1/repositories        # List repositories
POST   /api/v1/repositories        # Add repository
GET    /api/v1/repositories/{id}   # Get repository
PUT    /api/v1/repositories/{id}   # Update repository
DELETE /api/v1/repositories/{id}   # Delete repository
POST   /api/v1/repositories/{id}/clone
POST   /api/v1/repositories/{id}/detect-language
```

### Scans
```
GET    /api/v1/scans               # List scans
POST   /api/v1/scans               # Create scan
GET    /api/v1/scans/{id}          # Get scan
POST   /api/v1/scans/{id}/cancel   # Cancel scan
POST   /api/v1/scans/{id}/retry    # Retry scan
GET    /api/v1/scans/{id}/summary  # Scan summary
```

### Findings
```
GET    /api/v1/findings            # List findings
GET    /api/v1/findings/{id}       # Get finding
PUT    /api/v1/findings/{id}       # Update finding
POST   /api/v1/findings/{id}/explain  # AI explanation
GET    /api/v1/findings/stats/summary
```

### Patches
```
GET    /api/v1/patches             # List patches
GET    /api/v1/patches/{id}        # Get patch
POST   /api/v1/patches             # Generate patch
POST   /api/v1/patches/{id}/apply  # Apply patch
POST   /api/v1/patches/{id}/regenerate
```

### Reports
```
GET    /api/v1/reports             # List reports
POST   /api/v1/reports             # Generate report
GET    /api/v1/reports/{id}        # Get report
GET    /api/v1/reports/{id}/download
```

### Pull Requests
```
GET    /api/v1/pull-requests       # List PRs
POST   /api/v1/pull-requests       # Create PR
GET    /api/v1/pull-requests/{id}  # Get PR
POST   /api/v1/pull-requests/{id}/sync
```

### Chat Assistant
```
POST   /api/v1/chat                # Send message
POST   /api/v1/chat/explain-finding/{id}
```

## Development

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker
celery -A core.celery_app worker --loglevel=info

# Run Celery beat
celery -A core.celery_app beat --loglevel=info
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev
```

### Running Tests
```bash
# Backend tests
cd backend
pytest --cov=./ --cov-report=html

# Frontend tests
cd frontend
npm run test
```

### Code Quality
```bash
# Backend
cd backend
black .
isort .
ruff check .
mypy .

# Frontend
cd frontend
npm run lint
npm run format
```

## Deployment

### Production Deployment

1. **Prepare Environment**
   ```bash
   cp .env.example .env.production
   # Edit with production values
   ```

2. **Build Images**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
   ```

3. **Deploy**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

4. **Run Migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

### Kubernetes Deployment
Helm charts available in `deploy/kubernetes/`

### Monitoring
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin)
- **Jaeger**: http://localhost:16686

## Project Structure

```
ai-secure-code-reviewer/
├── backend/
│   ├── api/v1/              # REST API endpoints
│   ├── agents/              # AI agents
│   ├── core/                # Core configuration
│   ├── database/            # Database models & sessions
│   ├── github/              # GitHub integration
│   ├── models/              # SQLAlchemy models
│   ├── rag/                 # RAG engine
│   ├── schemas/             # Pydantic schemas
│   ├── security/            # Security scanners
│   ├── tasks/               # Celery tasks
│   ├── verification/        # Patch verification
│   ├── reports/             # Report generation
│   └── utils/               # Utilities
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── services/        # API services
│   │   ├── store/           # State management
│   │   ├── types/           # TypeScript types
│   │   └── utils/           # Utilities
│   └── public/
├── nginx/                   # Nginx configuration
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── .github/workflows/       # CI/CD pipelines
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow existing code style
- Write tests for new features
- Update documentation
- Ensure all CI checks pass

## Security

This project follows security best practices:
- All secrets managed via environment variables
- JWT-based authentication with refresh tokens
- Role-based access control (RBAC)
- Input validation and sanitization
- Rate limiting on API endpoints
- Security scanning in CI/CD pipeline
- Regular dependency updates

### Reporting Security Issues
Please report security vulnerabilities to security@your-org.com

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [OWASP](https://owasp.org/) for security standards
- [Semgrep](https://semgrep.dev/) for SAST engine
- [Bandit](https://bandit.readthedocs.io/) for Python security
- [Gitleaks](https://github.com/gitleaks/gitleaks) for secret detection
- [Trivy](https://trivy.dev/) for vulnerability scanning
- [ChromaDB](https://www.trychroma.com/) for vector storage
- [LangChain](https://langchain.com/) for AI orchestration

---

**Built with ❤️ for secure software development**