# Contributing to Nauyaca

Thank you for your interest in contributing to Nauyaca! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Guidelines](#testing-guidelines)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)
- [Getting Help](#getting-help)

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- **Python 3.11 or higher** (Python 3.14 recommended)
- **uv** - Fast Python package installer and resolver ([installation instructions](https://github.com/astral-sh/uv))
- **Git** for version control
- Basic familiarity with asyncio and the Gemini protocol (see [Resources](#resources))

### Finding Something to Work On

- Check the [issue tracker](https://github.com/alanbato/nauyaca/issues) for open issues
- Look for issues labeled `good first issue` for newcomer-friendly tasks
- Issues labeled `help wanted` are especially open to external contributions
- Feel free to propose new features or improvements by opening an issue first

## Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/nauyaca.git
   cd nauyaca
   ```

2. **Install dependencies**:
   ```bash
   # Install all dependencies including dev dependencies
   uv sync
   ```

3. **Install pre-commit hooks**:
   ```bash
   # Set up pre-commit hooks for automatic code quality checks
   uv run pre-commit install
   ```

4. **Verify your setup**:
   ```bash
   # Run the test suite
   uv run pytest

   # Run linting
   uv run ruff check src/ tests/

   # Run type checking
   uv run mypy src/
   ```

## Development Workflow

### Creating a Branch

Create a descriptive branch name following these conventions:

- `feat/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes
- `test/description` - Test additions or changes
- `refactor/description` - Code refactoring

Example:
```bash
git checkout -b feat/client-certificate-support
```

### Making Changes

1. **Write your code** following our [code standards](#code-standards)
2. **Add tests** for any new functionality
3. **Update documentation** if you're changing behavior or adding features
4. **Run the test suite** to ensure everything passes
5. **Commit your changes** using [conventional commit messages](#commit-messages)

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=src/nauyaca --cov-report=html

# Run specific test categories
uv run pytest -m unit          # Only unit tests
uv run pytest -m integration   # Only integration tests
uv run pytest -m "not slow"    # Exclude slow tests

# Run a specific test file
uv run pytest tests/test_server/test_handler.py

# Run a specific test function
uv run pytest tests/test_server/test_handler.py::test_static_file_serving

# Run tests in parallel (faster)
uv run pytest -n auto
```

### Code Quality Checks

Our pre-commit hooks will run automatically, but you can also run them manually:

```bash
# Run all pre-commit hooks
uv run pre-commit run --all-files

# Run linting
uv run ruff check src/ tests/

# Auto-fix linting issues
uv run ruff check --fix src/ tests/

# Run type checking
uv run mypy src/
```

## Code Standards

### Python Style

- Follow **PEP 8** style guidelines (enforced by Ruff)
- Use **type hints** for all function signatures (enforced by mypy)
- Maximum line length: **90 characters**
- Use **double quotes** for strings
- Import sorting follows isort conventions (enforced by Ruff)

### Type Hints

All functions must have complete type hints:

```python
# Good
def parse_url(url: str) -> ParsedURL:
    ...

# Bad - missing type hints
def parse_url(url):
    ...
```

### Docstrings

All public classes, methods, and functions must have docstrings following **Google style**:

```python
def fetch_gemini(url: str, timeout: int = 30) -> GeminiResponse:
    """Fetch a resource from a Gemini server.

    Args:
        url: The Gemini URL to fetch
        timeout: Request timeout in seconds

    Returns:
        A GeminiResponse object containing the server's response

    Raises:
        ValueError: If the URL is invalid
        TimeoutError: If the request times out

    Example:
        >>> response = fetch_gemini("gemini://example.com/")
        >>> print(response.status)
        20
    """
    ...
```

### Security Considerations

When contributing, be mindful of security:

- **Never commit secrets, API keys, or credentials**
- **Validate all user inputs** to prevent injection attacks
- **Use Path.resolve()** and validate paths to prevent directory traversal
- **Enforce size limits** on requests and responses
- **Follow the principle of least privilege**

See [SECURITY.md](SECURITY.md) for detailed security guidelines.

## Testing Guidelines

### Test Requirements

- All new features **must** include tests
- Bug fixes **should** include regression tests
- Aim for **≥80% code coverage**
- Tests should be **fast and isolated** (use mocks for external dependencies)

### Test Organization

- `tests/test_protocol/` - Protocol-level tests (request/response parsing)
- `tests/test_server/` - Server implementation tests
- `tests/test_client/` - Client implementation tests
- `tests/test_security/` - Security feature tests
- `tests/test_integration/` - End-to-end integration tests

### Writing Tests

Use pytest conventions and markers:

```python
import pytest
from nauyaca.client import GeminiClient

@pytest.mark.unit
def test_request_parsing():
    """Test that requests are parsed correctly."""
    request = parse_request("gemini://example.com/path\r\n")
    assert request.host == "example.com"
    assert request.path == "/path"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_request_cycle():
    """Test a complete client-server interaction."""
    async with GeminiClient() as client:
        response = await client.fetch("gemini://localhost:1965/")
        assert response.status == 20
```

### Test Markers

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Tests with real network connections
- `@pytest.mark.slow` - Long-running tests (>1 second)
- `@pytest.mark.network` - Tests requiring network access

## Submitting Changes

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions or changes
- `refactor:` - Code refactoring without behavior changes
- `perf:` - Performance improvements
- `chore:` - Build process or auxiliary tool changes

**Examples**:
```
feat(client): add support for client certificates

Implement client certificate authentication for requests that require
them. This allows servers to verify client identity.

Closes #123
```

```
fix(server): prevent path traversal in static file handler

Use Path.resolve() to canonicalize paths and validate they remain
within the document root.

Fixes #456
```

### Pull Request Process

1. **Ensure all tests pass** and code quality checks succeed
2. **Update documentation** if you're changing behavior
3. **Add an entry to CHANGELOG.md** (if one exists) describing your changes
4. **Create a pull request** with a clear title and description
5. **Link related issues** using keywords like "Closes #123" or "Fixes #456"
6. **Respond to review feedback** in a timely manner

### Pull Request Template

When creating a PR, include:

```markdown
## Description
Brief description of what this PR does

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update

## Testing
Describe the tests you added or how you tested your changes

## Checklist
- [ ] My code follows the project's code style
- [ ] I have added tests that prove my fix/feature works
- [ ] All tests pass locally
- [ ] I have updated the documentation accordingly
- [ ] My changes generate no new warnings
```

## Reporting Issues

### Bug Reports

When reporting bugs, please include:

- **Clear description** of the issue
- **Steps to reproduce** the problem
- **Expected behavior** vs. actual behavior
- **Environment details** (Python version, OS, nauyaca version)
- **Relevant logs or error messages**
- **Minimal code example** if applicable

### Feature Requests

When requesting features, please include:

- **Use case**: Why is this feature needed?
- **Proposed solution**: How should it work?
- **Alternatives considered**: What other approaches did you consider?
- **Additional context**: Any other relevant information

## Getting Help

- **Documentation**: Check the [README](README.md) and [SECURITY.md](SECURITY.md)
- **Issues**: Search existing issues before creating a new one
- **Discussions**: Use GitHub Discussions for questions and general discussion
- **Email**: For sensitive matters, contact alanvelasco.a@gmail.com

## Resources

### Learning About Gemini Protocol

- [Project Gemini Official Site](https://gemini.circumlunar.space/)
- [Gemini Protocol Specification](https://gemini.circumlunar.space/docs/specification.gmi)
- [Awesome Gemini](https://github.com/kr1sp1n/awesome-gemini) - Curated list of Gemini resources

### Python asyncio Resources

- [asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [asyncio Protocol/Transport Pattern](https://docs.python.org/3/library/asyncio-protocol.html)
- See `sample/GEMINI_ASYNCIO_GUIDE.md` in this repository

### Project-Specific Documentation

- `CLAUDE.md` - Detailed project architecture and implementation guide
- `SECURITY.md` - Security features and best practices
- `sample/` - Reference implementations and guides

## Recognition

Contributors are recognized in several ways:

- Listed in the project's contributors page
- Mentioned in release notes for significant contributions
- Added to a CONTRIBUTORS file (if created)

Thank you for contributing to Nauyaca! 🐍✨
