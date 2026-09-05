#!/usr/bin/env python3
"""
Test Runner Script for AI Secure Code Reviewer
Runs all tests with proper configuration
"""
import argparse
import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd: list, cwd: str = None, env: dict = None) -> int:
    """Run command and return exit code"""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    
    use_shell = sys.platform == "win32"
    result = subprocess.run(cmd, cwd=cwd, env=full_env, shell=use_shell)
    return result.returncode


def run_backend_tests(args):
    """Run backend tests"""
    backend_dir = Path("backend")
    
    # Set test environment
    test_env = {
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/1",
        "CHROMADB_URL": "http://localhost:8000",
        "SECRET_KEY": "test-secret-key-for-testing-only-32-chars",
        "GEMINI_API_KEY": "test-key",
        "DEFAULT_LLM_PROVIDER": "gemini",
        "DEFAULT_MODEL": "gemini-1.5-flash",
        "OPENAI_API_KEY": "test-key",
        "LOG_LEVEL": "DEBUG",
        "ENVIRONMENT": "test",
    }
    
    cmd = ["pytest"]
    
    if args.coverage:
        cmd.extend(["--cov=./", "--cov-report=html", "--cov-report=term-missing"])
    
    if args.verbose:
        cmd.append("-v")
    
    if args.keyword:
        cmd.extend(["-k", args.keyword])
    
    if args.marker:
        cmd.extend(["-m", args.marker])
    
    if args.junit:
        cmd.extend(["--junitxml=test-results.xml"])
    
    return run_command(cmd, cwd=backend_dir, env=test_env)


def run_frontend_tests(args):
    """Run frontend tests"""
    frontend_dir = Path("frontend")
    
    cmd = ["npm", "run", "test", "--", "--run"]
    
    if args.coverage:
        cmd.extend(["--coverage"])
    
    if args.verbose:
        cmd.append("--reporter=verbose")
    
    return run_command(cmd, cwd=frontend_dir)


def run_playwright_tests(args):
    """Run Playwright E2E tests"""
    frontend_dir = Path("frontend")
    
    cmd = ["npx", "playwright", "test"]
    
    if args.headed:
        cmd.append("--headed")
    
    if args.debug:
        cmd.append("--debug")
    
    if args.project:
        cmd.extend(["--project", args.project])
    
    if args.test_file:
        cmd.append(args.test_file)
    
    return run_command(cmd, cwd=frontend_dir)


def run_linting(args):
    """Run all linting"""
    exit_codes = []
    
    # Backend linting
    print("\n🔍 Backend Linting...")
    backend_dir = Path("backend")
    exit_codes.append(run_command(["ruff", "check", "."], cwd=backend_dir))
    exit_codes.append(run_command(["black", "--check", "."], cwd=backend_dir))
    exit_codes.append(run_command(["isort", "--check", "."], cwd=backend_dir))
    exit_codes.append(run_command(["mypy", "."], cwd=backend_dir))
    
    # Frontend linting
    print("\n🔍 Frontend Linting...")
    frontend_dir = Path("frontend")
    exit_codes.append(run_command(["npm", "run", "lint"], cwd=frontend_dir))
    
    return max(exit_codes) if exit_codes else 0


def run_type_checking(args):
    """Run type checking"""
    print("\n🔍 Type Checking...")
    frontend_dir = Path("frontend")
    return run_command(["npx", "tsc", "--noEmit"], cwd=frontend_dir)


def run_security_scan(args):
    """Run security scans"""
    print("\n🔍 Security Scans...")
    exit_codes = []
    
    # Trivy
    exit_codes.append(run_command([
        "docker", "run", "--rm",
        "-v", f"{os.getcwd()}:/workspace",
        "aquasec/trivy:latest",
        "fs", "--format", "sarif", "--output", "trivy-results.sarif",
        "--severity", "HIGH,CRITICAL", "/workspace"
    ]))
    
    # Semgrep (if available)
    try:
        exit_codes.append(run_command(["semgrep", "--config=auto", "."]))
    except FileNotFoundError:
        print("⚠️  Semgrep not installed, skipping...")
    
    # Bandit
    try:
        exit_codes.append(run_command(["bandit", "-r", "backend/", "-f", "json", "-o", "bandit-results.json"]))
    except FileNotFoundError:
        print("⚠️  Bandit not installed, skipping...")
    
    return max(exit_codes) if exit_codes else 0


def main():
    parser = argparse.ArgumentParser(description="Test Runner for AI Secure Code Reviewer")
    parser.add_argument("--backend", action="store_true", help="Run backend tests")
    parser.add_argument("--frontend", action="store_true", help="Run frontend tests")
    parser.add_argument("--e2e", action="store_true", help="Run Playwright E2E tests")
    parser.add_argument("--lint", action="store_true", help="Run linting")
    parser.add_argument("--typecheck", action="store_true", help="Run type checking")
    parser.add_argument("--security", action="store_true", help="Run security scans")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    # Test options
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-k", "--keyword", help="Run tests matching keyword")
    parser.add_argument("-m", "--marker", help="Run tests with marker")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--junit", action="store_true", help="Generate JUnit XML")
    
    # Playwright options
    parser.add_argument("--headed", action="store_true", help="Run Playwright in headed mode")
    parser.add_argument("--debug", action="store_true", help="Run Playwright in debug mode")
    parser.add_argument("--project", help="Playwright project to run")
    parser.add_argument("--test-file", help="Specific test file to run")
    
    args = parser.parse_args()
    
    # Default to all if no specific test type selected
    if not any([args.backend, args.frontend, args.e2e, args.lint, args.typecheck, args.security]):
        args.all = True
    
    exit_codes = []
    
    if args.all or args.lint:
        exit_codes.append(run_linting(args))
    
    if args.all or args.typecheck:
        exit_codes.append(run_type_checking(args))
    
    if args.all or args.backend:
        exit_codes.append(run_backend_tests(args))
    
    if args.all or args.frontend:
        exit_codes.append(run_frontend_tests(args))
    
    if args.all or args.e2e:
        exit_codes.append(run_playwright_tests(args))
    
    if args.all or args.security:
        exit_codes.append(run_security_scan(args))
    
    # Overall result
    final_code = max(exit_codes) if exit_codes else 0
    
    print(f"\n{'='*60}")
    if final_code == 0:
        print("[SUCCESS] All tests passed!")
    else:
        print(f"[FAILED] Some tests failed (exit code: {final_code})")
    print(f"{'='*60}")
    
    sys.exit(final_code)


if __name__ == "__main__":
    main()