# Enable Hot-Reload for Development

This guide shows you how to use hot-reload functionality to automatically restart your Gemini server when files change during development.

!!! warning "Development Only"
    Hot-reload is designed for development environments only. Never use it in production - it adds overhead and is not suitable for serving real traffic.

## What is Hot-Reload?

Hot-reload automatically restarts your Gemini server when source files or content files change. This eliminates the need to manually stop and restart the server every time you modify your code or update your Gemini content.

**Use hot-reload when:**

- Developing server handlers or middleware
- Creating or editing Gemini content (`.gmi` files)
- Testing configuration changes
- Iterating on server features

**Key features:**

- Automatic file watching with OS-native events (when available)
- Graceful server restarts on changes
- Configurable watch directories and file extensions
- Minimal performance overhead during development

## Quick Start

### Basic Usage

Enable hot-reload with the `--reload` flag:

```bash
nauyaca serve ./capsule --reload
```

This watches for changes in:

- Your document root (`./capsule`)
- The Nauyaca source directory (`src/nauyaca`)

And monitors these file extensions:

- `.py` - Python source files
- `.gmi` - Gemini text files

When you modify any matching file, the server automatically restarts.

### Watch Custom Directories

Use `--reload-dir` to specify additional directories to watch:

```bash
# Watch a single custom directory
nauyaca serve ./capsule --reload --reload-dir ./my-handlers

# Watch multiple directories (repeat the flag)
nauyaca serve ./capsule --reload \
    --reload-dir ./my-handlers \
    --reload-dir ./templates
```

!!! tip "Default Directories Still Watched"
    When you specify custom directories with `--reload-dir`, the server ONLY watches those directories. If you want to also watch the default directories (document root and source), you must include them explicitly.

### Watch Additional File Extensions

Use `--reload-ext` to watch additional file types:

```bash
# Also watch TOML configuration files
nauyaca serve ./capsule --reload --reload-ext .toml

# Watch multiple extensions
nauyaca serve ./capsule --reload \
    --reload-ext .toml \
    --reload-ext .txt \
    --reload-ext .md
```

!!! note "Extension Format"
    Extensions can be specified with or without the leading dot (`.py` or `py` both work).

## Common Workflows

### Content Development

When working on Gemini content:

```bash
# Watch only your capsule directory
nauyaca serve ./capsule --reload --reload-dir ./capsule
```

Now edit your `.gmi` files - the server restarts automatically when you save.

### Full-Stack Development

When developing both code and content:

```bash
# Watch source code and content
nauyaca serve ./capsule --reload \
    --reload-dir ./src/nauyaca \
    --reload-dir ./capsule
```

### Configuration Development

When testing configuration changes:

```bash
# Watch config files too
nauyaca serve --config config.toml --reload \
    --reload-dir ./capsule \
    --reload-ext .toml
```

Now changes to `config.toml` trigger a restart.

### Custom Handler Development

When building custom request handlers:

```bash
# Watch your handler directory and capsule
nauyaca serve ./capsule --reload \
    --reload-dir ./my_handlers \
    --reload-dir ./capsule
```

## How It Works

### File Watching Backends

Nauyaca uses two file watching strategies:

1. **watchfiles** (preferred): Fast, OS-native file watching using:
   - `inotify` on Linux
   - `FSEvents` on macOS
   - `ReadDirectoryChangesW` on Windows

2. **Polling** (fallback): Periodically scans directories for changes
   - Used when `watchfiles` is not installed
   - Slower but works everywhere

#### Installing watchfiles

For best performance, install the `watchfiles` library:

```bash
# With uv
uv pip install watchfiles

# With pip
pip install watchfiles
```

If `watchfiles` is not available, Nauyaca automatically falls back to polling with a 1-second interval.

### Restart Process

When files change:

1. **Detection**: File watcher detects changes matching watched extensions
2. **Logging**: Server logs which files changed (up to 5 shown)
3. **Graceful shutdown**: Current server receives SIGTERM and has 10 seconds to shut down cleanly
4. **Force kill**: If shutdown takes longer than 10 seconds, server is forcefully terminated
5. **Port release**: Brief 0.5 second pause to allow OS to release the port
6. **Restart**: New server process starts with the same arguments

### Supervisor Architecture

Hot-reload uses a supervisor process pattern:

```
┌─────────────────────┐
│   Supervisor        │  ← Main process with file watcher
│   (parent process)  │
└──────────┬──────────┘
           │
           │ spawns
           ↓
┌─────────────────────┐
│   Server            │  ← Server subprocess
│   (child process)   │
└─────────────────────┘
```

The supervisor:

- Watches files for changes
- Spawns/restarts the server subprocess
- Handles SIGINT/SIGTERM for clean shutdown
- Manages server lifecycle

## Verification

### Check Hot-Reload is Active

When you start the server with `--reload`, you'll see:

```
[Reload] Hot-reload enabled
[Reload] Watching: /home/user/capsule, /home/user/src/nauyaca
[Reload] Extensions: .py, .gmi
```

### Test File Change Detection

1. Start the server with reload:
   ```bash
   nauyaca serve ./capsule --reload
   ```

2. Edit a `.gmi` file in `./capsule`:
   ```bash
   echo "# Updated Content" >> ./capsule/index.gmi
   ```

3. Check the logs - you should see:
   ```
   [INFO] reload_triggered: Changed files: ['/home/user/capsule/index.gmi']
   [INFO] stopping_server: pid=12345
   [INFO] starting_server: command=python -m nauyaca serve ./capsule
   ```

### Verify Backend

Check which backend is being used:

```
# With watchfiles installed:
[INFO] file_watcher_created: backend=watchfiles

# Without watchfiles (fallback):
[WARNING] watchfiles_not_available: fallback=polling hint=pip install watchfiles
```

## Troubleshooting

### Server Not Restarting on Changes

**Problem**: Files change but server doesn't restart.

**Solutions**:

1. Check the file extension is being watched:
   ```bash
   # For .toml files, add --reload-ext
   nauyaca serve ./capsule --reload --reload-ext .toml
   ```

2. Check the directory is being watched:
   ```bash
   # Explicitly watch the directory
   nauyaca serve ./capsule --reload --reload-dir ./capsule
   ```

3. Check the logs for "changes_filtered" messages indicating files were ignored

### Permission Errors

**Problem**: `Permission denied` errors when accessing files.

**Solution**: Ensure your user has read permissions on all watched directories:

```bash
# Check permissions
ls -la ./capsule

# Fix if needed
chmod -R u+r ./capsule
```

### Port Already in Use After Restart

**Problem**: "Address already in use" errors during restart.

**Cause**: Previous server didn't release the port in time.

**Solution**: This should resolve automatically after the 0.5s port release delay. If persistent:

1. Reduce restart frequency by fixing errors before saving
2. Check no other process is using port 1965:
   ```bash
   # Linux/macOS
   lsof -i :1965

   # Kill stray process if needed
   kill <PID>
   ```

### Too Many Files Being Watched

**Problem**: High CPU usage or slow restarts.

**Solution**: Be more selective about watched directories:

```bash
# Instead of watching entire source tree:
nauyaca serve ./capsule --reload --reload-dir ./src

# Watch only specific subdirectories:
nauyaca serve ./capsule --reload --reload-dir ./src/nauyaca/server
```

### Recursion Warning

**Problem**: "Detected reload recursion" in logs.

**Cause**: Server arguments include `--reload` flag, causing supervisor to spawn another supervisor.

**Solution**: This should never happen (Nauyaca filters reload flags automatically). If you see this:

1. Check you're not setting `--reload` in a config file
2. Report as a bug

## Advanced Configuration

### Custom Polling Interval

The polling backend checks for changes every 1 second by default. This is not currently configurable via CLI but can be customized programmatically:

```python
from pathlib import Path
from nauyaca.server.reload import ReloadConfig, run_with_reload

config = ReloadConfig(
    watch_dirs=[Path("./capsule")],
    watch_extensions=[".py", ".gmi"],
    polling_interval=2.0  # Check every 2 seconds
)

run_with_reload(config, ["serve", "./capsule"])
```

### Exclude Specific Files

Currently, hot-reload watches all files with matching extensions. To exclude files:

1. Use a different extension for files you want ignored
2. Move them outside watched directories
3. Use `.gitignore` style patterns (planned feature)

## See Also

- **[Configure Server](configure-server.md)**: Configure server settings that affect reload behavior
- **[Logging](logging.md)**: Configure logging to track reload events
- **[CLI Reference](../reference/cli.md)**: Complete CLI documentation including all reload flags
- **[Architecture](../explanation/architecture.md)**: Learn about the server architecture
