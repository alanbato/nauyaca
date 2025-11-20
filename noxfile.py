import nox

PYPROJECT = nox.project.load_toml("pyproject.toml")
PYTHON_VERSIONS = nox.project.python_versions(PYPROJECT)

nox.options.default_venv_backend = "uv"


@nox.session(python=["3.10", "3.11", "3.12", "3.13", "3.14"])
def lint(session):
    session.install(".[dev]")
    session.run("uv", "run", "ruff", "check", ".")


@nox.session(python=["3.10", "3.11", "3.12", "3.13", "3.14"])
def test(session):
    session.install(".[dev]")
    session.run(
        "uv", "run", "pytest", "-m", "not slow and not integration and not network"
    )


@nox.session(python=["3.10", "3.11", "3.12", "3.13", "3.14"], default=False)
def test_full(session):
    session.install(".[dev]")
    session.run("uv", "run", "pytest")
