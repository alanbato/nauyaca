# Installation

This guide will help you install Nauyaca on your system. Choose the installation method that best fits your needs.

## Prerequisites

Before installing Nauyaca, ensure you have:

- **Python 3.10 or higher** installed on your system
- **pip** (included with Python) or **uv** (recommended for faster installations)

!!! tip "Why uv?"
    [uv](https://docs.astral.sh/uv/) is a modern, extremely fast Python package manager written in Rust. It's 10-100x faster than pip and provides better dependency resolution. We recommend using uv for the best experience.

### Checking Your Python Version

```bash
python --version
```

You should see Python 3.10.x or higher. If not, download the latest version from [python.org](https://www.python.org/downloads/).

### Installing uv (Recommended)

=== "Linux/macOS"

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows"

    ```powershell
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

=== "Using pip"

    ```bash
    pip install uv
    ```

## Installation Methods

### Method 1: Install as a CLI Tool (Recommended)

This is the recommended method if you want to use Nauyaca primarily as a command-line tool for running servers and clients.

=== "Using uv"

    ```bash
    uv tool install nauyaca
    ```

    This installs the `nauyaca` command globally, making it available from anywhere on your system.

=== "Using pipx"

    ```bash
    pipx install nauyaca
    ```

    [pipx](https://pipx.pypa.io/) is similar to uv tool install - it installs CLI tools in isolated environments.

After installation, verify it works:

```bash
nauyaca --help
```

You should see the Nauyaca command-line interface help text.

### Method 2: Install as a Library

This method is best if you want to use Nauyaca in your own Python projects or applications.

=== "Using uv (New Project)"

    ```bash
    # Create a new project
    uv init my-gemini-project
    cd my-gemini-project

    # Add nauyaca as a dependency
    uv add nauyaca
    ```

=== "Using uv (Existing Project)"

    ```bash
    # Add to your existing project
    uv add nauyaca
    ```

=== "Using pip"

    ```bash
    # In a virtual environment (recommended)
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install nauyaca
    ```

    ```bash
    # Or install system-wide (not recommended)
    pip install nauyaca
    ```

### Method 3: Install from Source (Development)

This method is for developers who want to contribute to Nauyaca or test the latest unreleased features.

```bash
# Clone the repository
git clone https://github.com/alanbato/nauyaca.git
cd nauyaca

# Install with development dependencies
uv sync
```

!!! warning "Development Installation"
    Installing from source gives you the latest development version, which may be unstable. For production use, install from PyPI using Method 1 or 2.

## Verifying Your Installation

After installation, verify that Nauyaca is working correctly:

### Check the Version

```bash
nauyaca version
```

Expected output:
```
Nauyaca version 0.2.0
```

### Run the Help Command

```bash
nauyaca --help
```

You should see output similar to:

```
Usage: nauyaca [OPTIONS] COMMAND [ARGS]...

  Nauyaca - Modern Gemini Protocol Server & Client

Commands:
  serve    Start a Gemini server
  get      Fetch a Gemini resource
  cert     Certificate management
  tofu     Manage TOFU database
  version  Show version information
```

### Test the Client

Try fetching a resource from a public Gemini server:

```bash
nauyaca get gemini://geminiprotocol.net/
```

!!! note "First Connection"
    On your first connection to a server, you'll be prompted to trust the certificate (TOFU - Trust On First Use). This is normal and expected.

## Optional: Shell Completion

Nauyaca supports shell completion for Bash, Zsh, and Fish. This provides tab-completion for commands and options.

=== "Bash"

    ```bash
    # Add to ~/.bashrc
    eval "$(_NAUYACA_COMPLETE=bash_source nauyaca)"
    ```

    Then reload your shell:
    ```bash
    source ~/.bashrc
    ```

=== "Zsh"

    ```bash
    # Add to ~/.zshrc
    eval "$(_NAUYACA_COMPLETE=zsh_source nauyaca)"
    ```

    Then reload your shell:
    ```bash
    source ~/.zshrc
    ```

=== "Fish"

    ```bash
    # Add to ~/.config/fish/completions/nauyaca.fish
    _NAUYACA_COMPLETE=fish_source nauyaca | source
    ```

    Then reload your shell:
    ```bash
    source ~/.config/fish/config.fish
    ```

## Development Setup

If you're planning to contribute to Nauyaca or develop with the source code, follow these additional steps:

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/alanbato/nauyaca.git
cd nauyaca

# Install with development dependencies
uv sync
```

### 2. Verify the Test Suite

Run the test suite to ensure everything is working:

```bash
uv run pytest
```

Expected output:
```
================================ test session starts ================================
...
================================ XX passed in X.XXs =================================
```

### 3. Run Code Quality Checks

```bash
# Run linting
uv run ruff check src/ tests/

# Run type checking
uv run mypy src/

# Run tests with coverage
uv run pytest --cov=src/nauyaca --cov-report=html
```

### 4. Pre-commit Hooks (Optional)

Install pre-commit hooks to automatically run checks before each commit:

```bash
uv run pre-commit install
```

## Troubleshooting

### Python Version Issues

**Problem**: `nauyaca` command not found after installation

**Solution**: Ensure your Python bin directory is in your PATH:

=== "Linux/macOS"

    ```bash
    # For uv tool install
    export PATH="$HOME/.local/bin:$PATH"

    # Add to ~/.bashrc or ~/.zshrc to make permanent
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    ```

=== "Windows"

    Add `%USERPROFILE%\AppData\Local\bin` to your PATH environment variable.

### SSL/TLS Certificate Errors

**Problem**: Certificate verification errors when connecting to servers

**Solution**: This is usually due to self-signed certificates. Nauyaca uses TOFU validation, so you'll need to trust certificates on first use:

```bash
# Manually trust a certificate
nauyaca tofu trust geminiprotocol.net
```

### Import Errors in Python

**Problem**: `ModuleNotFoundError: No module named 'nauyaca'`

**Solution**: Ensure you've installed nauyaca in your current Python environment:

```bash
# Check if nauyaca is installed
pip list | grep nauyaca

# If not found, install it
uv add nauyaca  # or: pip install nauyaca
```

### Permission Errors

**Problem**: Permission denied errors during installation

**Solution**:

- **Don't use sudo with pip** - Use a virtual environment instead
- **For uv tool install** - No sudo needed, installs to user directory
- **If you must install system-wide** - Consider using your OS package manager

## Upgrading Nauyaca

To upgrade to the latest version:

=== "Using uv tool"

    ```bash
    uv tool upgrade nauyaca
    ```

=== "Using pip"

    ```bash
    pip install --upgrade nauyaca
    ```

=== "From source"

    ```bash
    cd nauyaca
    git pull origin main
    uv sync
    ```

## Uninstalling

If you need to remove Nauyaca:

=== "Using uv tool"

    ```bash
    uv tool uninstall nauyaca
    ```

=== "Using pip"

    ```bash
    pip uninstall nauyaca
    ```

=== "From source"

    Simply delete the cloned repository directory:
    ```bash
    rm -rf nauyaca
    ```

## Next Steps

Now that you have Nauyaca installed, you can:

- **[Quickstart Guide](quickstart.md)** - Get started with your first Gemini server
- **[Server Configuration](reference/configuration.md)** - Learn about configuration options
- **[Client API](reference/api/client.md)** - Use Nauyaca as a Gemini client
- **[Security Model](explanation/security-model.md)** - Understand TOFU validation and security features

## See Also

- [PyPI Package](https://pypi.org/project/nauyaca/) - Official package on PyPI
- [GitHub Repository](https://github.com/alanbato/nauyaca) - Source code and issues
- [uv Documentation](https://docs.astral.sh/uv/) - Learn more about uv
