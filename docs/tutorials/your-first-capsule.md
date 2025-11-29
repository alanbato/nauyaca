# Your First Gemini Capsule

Welcome! This tutorial will guide you through creating and serving your first Gemini capsule (the Gemini equivalent of a website). By the end, you'll have a personal capsule with multiple pages that you can browse using the Gemini protocol.

## What is a Gemini Capsule?

A Gemini **capsule** is a collection of content served over the Gemini protocol, similar to how a website is served over HTTP. Instead of HTML, Gemini uses a lightweight markup language called **gemtext** (`.gmi` files) that's designed to be simple, accessible, and easy to write.

## What We'll Build

In this tutorial, we'll create a personal capsule with:

- A home page with a welcome message
- An about page with personal information
- A blog section with your first post
- Proper navigation between pages

The entire process takes about 10-15 minutes!

## Prerequisites

Before starting, make sure you have Nauyaca installed:

```bash
# Install with uv (recommended)
uv pip install nauyaca

# Or with pip
pip install nauyaca

# Verify installation
nauyaca version
```

You should see output showing Nauyaca version 0.1.0 or higher.

## Step 1: Create Your Capsule Directory

First, let's create a directory structure for your capsule. Open a terminal and run:

```bash
# Create the main capsule directory
mkdir -p my-capsule/blog

# Navigate into it
cd my-capsule
```

Your directory structure should now look like this:

```
my-capsule/
└── blog/
```

!!! tip "Directory Organization"
    You can organize your capsule however you like! Common patterns include directories for `/blog`, `/projects`, `/links`, or `/art`. The Gemini protocol treats everything as simple file paths.

## Step 2: Create Your Home Page

Create a file named `index.gmi` in your `my-capsule` directory. This will be your home page.

```bash
# Create and edit index.gmi (use your favorite editor)
nano index.gmi
```

Add the following gemtext content:

```gemtext
# Welcome to My Gemini Capsule

Hello! This is my personal space on Geminispace.

## About This Capsule

This capsule is a simple collection of my thoughts, projects, and links. Gemini's minimalist approach helps me focus on content over presentation.

## Navigation

=> about.gmi About Me
=> blog/ My Blog

## What is Gemini?

Gemini is a protocol that sits between Gopher and HTTP - simple enough to be implementable in a weekend, but powerful enough for rich content. No tracking, no ads, just text and links.

---

Last updated: 2025-11-29
```

### Understanding Gemtext Basics

Let's break down what we just wrote:

- **`# Heading`** - Creates a top-level heading (use `##` or `###` for sub-headings)
- **`=> url Link Text`** - Creates a link (links always start on their own line)
- **`---`** - Not special in gemtext, just renders as three dashes (for visual separation)
- **Plain text** - Everything else is just regular text, one line per paragraph

!!! note "Long Lines"
    Gemtext uses "long lines" - don't manually wrap text at 80 characters. The client will wrap text to fit the screen. Use one line per paragraph.

## Step 3: Create Your About Page

Create `about.gmi`:

```bash
nano about.gmi
```

Add your personal information:

```gemtext
# About Me

## Who Am I?

I'm a Gemini enthusiast exploring the small web. I believe in simple, accessible content that focuses on substance over style.

## Interests

* Reading and writing
* Technology and programming
* Minimalist design
* Privacy and digital rights

## Contact

=> mailto:you@example.com Email me
=> gemini://other-capsule.com/ My other capsule

## Navigation

=> index.gmi Back to Home
=> blog/ Visit My Blog
```

Notice the **list syntax** (`* Item`) - each list item starts with an asterisk and space.

!!! warning "Email Links"
    Email links (`mailto:`) work in gemtext, but not all Gemini clients support them. It's often better to just write your email as plain text.

## Step 4: Create Your First Blog Post

Now let's create a blog post:

```bash
nano blog/first-post.gmi
```

Add your first post:

```gemtext
# My First Gemini Blog Post

Published: 2025-11-29

## Why I'm Trying Gemini

I've been exploring alternatives to the modern web, and Gemini caught my attention. Here's what I like about it:

* No JavaScript, no tracking, no ads
* Simple markup that's easy to write
* Focus on content, not presentation
* Lightweight and fast

## What I've Learned So Far

Getting started was surprisingly easy. I installed Nauyaca, created some .gmi files, and had a working capsule in minutes.

> Gemini feels like the early web - simple, personal, and focused on sharing ideas rather than maximizing engagement.

## Code Example

Here's how you start a Nauyaca server:

```
nauyaca serve ./my-capsule
```

That's it! No complex configuration needed for basic usage.

## Next Steps

I plan to:

* Write more blog posts
* Explore other capsules in Geminispace
* Maybe add some ASCII art
* Learn about client certificates

=> /index.gmi Back to Home
=> /about.gmi About Me
```

Notice the **blockquote** (`> Text`) and **preformatted text** (enclosed in ` ``` `) - these are used for quotes and code blocks respectively.

!!! tip "Preformatted Text"
    Everything between ` ``` ` lines is displayed exactly as written in a monospace font, perfect for code, ASCII art, or data tables.

## Step 5: Create a Blog Index

Let's add an index page for your blog directory:

```bash
nano blog/index.gmi
```

Add:

```gemtext
# My Blog

Welcome to my blog! I write about technology, Gemini, and whatever interests me.

## Recent Posts

=> first-post.gmi My First Gemini Blog Post (2025-11-29)

More posts coming soon!

=> /index.gmi Back to Home
```

## Step 6: Start Your Server

Now comes the exciting part - serving your capsule! Run:

```bash
nauyaca serve .
```

### What You Should See

You should see output similar to:

```
[Server] Starting Gemini server...
[Server] Document root: /home/you/my-capsule
[Server] Listening on localhost:1965
[Server] Using auto-generated self-signed certificate
[Server] Certificate fingerprint: a1b2c3d4e5f6...
[Server] Press Ctrl+C to stop
```

!!! note "Self-Signed Certificates"
    Nauyaca automatically generates a self-signed TLS certificate for testing. This is perfect for local development. For production, you'll want to create a proper certificate (see the security tutorial).

Your capsule is now live on `gemini://localhost:1965/`!

## Step 7: Browse Your Capsule

Open a **new terminal** (keep the server running) and test your capsule:

```bash
# Get your home page
nauyaca get gemini://localhost:1965/
```

### What You Should See

You should see your home page content displayed:

```
# Welcome to My Gemini Capsule

Hello! This is my personal space on Geminispace.

## About This Capsule
...
```

Now try navigating to other pages:

```bash
# View your about page
nauyaca get gemini://localhost:1965/about.gmi

# View your blog
nauyaca get gemini://localhost:1965/blog/

# View your first post
nauyaca get gemini://localhost:1965/blog/first-post.gmi
```

!!! tip "Verbose Mode"
    Add `-v` to see response headers: `nauyaca get -v gemini://localhost:1965/`

### Testing in the Server Terminal

Switch back to your server terminal - you should see access logs:

```
[2025-11-29 10:30:15] [INFO] Request: gemini://localhost:1965/ - Status: 20
[2025-11-29 10:30:18] [INFO] Request: gemini://localhost:1965/about.gmi - Status: 20
```

Each successful request shows status `20` (SUCCESS).

## Step 8: Experiment with Your Content

Now that your capsule is running, try making some changes:

1. Edit `index.gmi` and add a new section
2. Save the file
3. Run `nauyaca get gemini://localhost:1965/` again
4. See your changes instantly!

The server automatically serves the latest version of your files - no restart needed!

!!! tip "Common Mistake: File Extensions"
    Always use `.gmi` for gemtext files, not `.txt` or `.md`. The server uses the extension to set the correct MIME type (`text/gemini`).

## Step 9: Add Configuration (Optional)

For more control, you can create a configuration file. Create `config.toml` in your capsule directory:

```bash
nano config.toml
```

Add:

```toml
[server]
# Path to your gemini content
document_root = "."

# Server settings
host = "localhost"
port = 1965

# Enable directory listings for directories without index.gmi
enable_directory_listing = true

[logging]
level = "INFO"
```

Now start your server with the config file:

```bash
nauyaca serve --config config.toml
```

With `enable_directory_listing = true`, if you navigate to a directory without an `index.gmi`, the server will show a listing of files instead of an error.

!!! note "Configuration Flexibility"
    CLI arguments override config file values. For example: `nauyaca serve --config config.toml --port 8080`

## Gemtext Syntax Reference

Here's a quick reference for the gemtext you've learned:

| Syntax | Purpose | Example |
|--------|---------|---------|
| `# Heading` | Level 1 heading | `# Welcome` |
| `## Heading` | Level 2 heading | `## About` |
| `### Heading` | Level 3 heading | `### Details` |
| `=> url Label` | Link | `=> about.gmi About Me` |
| `* Item` | List item | `* First item` |
| `> Quote` | Blockquote | `> A wise saying` |
| ` ``` ` | Preformatted text toggle | ` ```code here``` ` |
| Plain text | Paragraph | `This is a paragraph.` |

!!! tip "Links Are Special"
    Unlike Markdown or HTML, you **cannot** make a word in the middle of a sentence into a link. Links always appear on their own line. This makes them easy to find and clients can style them distinctively.

## What You've Accomplished

Congratulations! You've:

- ✅ Created a Gemini capsule with multiple pages
- ✅ Written content using gemtext markup
- ✅ Started a Gemini server
- ✅ Browsed your capsule using the Gemini protocol
- ✅ Learned the basics of gemtext syntax
- ✅ (Optional) Created a configuration file

## Common Issues & Solutions

### Problem: "Address already in use"

**Cause**: Another process is using port 1965, or your server is already running.

**Solution**: Stop the other server, or use a different port:
```bash
nauyaca serve . --port 1966
```

### Problem: "Permission denied" on port 1965

**Cause**: Ports below 1024 require root privileges on most systems. Port 1965 is fine, but if you try port 965 you'll hit this.

**Solution**: Use a port above 1024, or run with `sudo` (not recommended for testing).

### Problem: Links show "51 NOT FOUND"

**Cause**: The file path in your link doesn't match the actual file.

**Solution**:
- Check file names match exactly (case-sensitive!)
- Links are relative to document root
- `=> about.gmi` looks for `about.gmi` in the same directory
- `=> /about.gmi` looks for `about.gmi` in the document root

## Next Steps

Now that you have a working capsule, here are some directions to explore:

### Explore Geminispace

Use your Nauyaca client to visit other capsules:

```bash
# Try the official Gemini project page
nauyaca get gemini://gemini.circumlunar.space/

# Explore a Gemini search engine
nauyaca get gemini://geminispace.info/
```

### Learn About Security

When you're ready to make your capsule public, read:

- **[Securing Your Server](securing-your-server.md)** - TLS certificates, rate limiting, and access control
- **[Server Configuration Reference](../reference/configuration.md)** - All configuration options

### Add More Features

- **Rate Limiting**: Protect against DoS attacks (enabled by default!)
- **Access Control**: Restrict access by IP address
- **Client Certificates**: Require authentication for certain paths
- **Custom Error Pages**: Personalize your 404 pages

### Join the Community

- Browse the Gemini protocol specification
- Visit other capsules and see what people are creating
- Share your capsule (when you're ready!)

## Further Reading

- [Gemtext Format Specification](../gemini_protocol/gemtext.txt) - Complete gemtext syntax guide
- [How-to: Configure Server](../how-to/configure-server.md) - Full server configuration options
- [Reference: CLI Commands](../reference/cli.md) - All Nauyaca commands
- [Explanation: Gemini Protocol](../explanation/gemini-protocol.md) - Protocol overview and philosophy

---

**Happy exploring Geminispace!** 🚀

If you have questions or run into issues, consult the [How-to Guides](../how-to/index.md) or check the project documentation.
