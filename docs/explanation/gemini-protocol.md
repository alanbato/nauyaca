# The Gemini Protocol

## What is Gemini?

Gemini is a modern internet protocol designed to occupy the space between Gopher and the Web. It prioritizes simplicity, privacy, and content over features, providing a lightweight alternative to HTTP/HTTPS for publishing and browsing content.

Created in 2019 by Solderpunk, Gemini deliberately avoids the complexity that has accumulated in the Web ecosystem while offering more capabilities than classic Gopher. It's not meant to replace the Web, but to exist alongside it as a complementary space for different kinds of content and interaction.

## Core Design Principles

### Mandatory Security

Unlike HTTP (which made HTTPS optional), Gemini **requires** TLS 1.2 or higher for all connections. There is no plaintext fallback. This means:

- All Gemini traffic is encrypted by default
- Privacy and security are built-in, not bolted on
- No need for users to check for "https://" - security is guaranteed

### Radical Simplicity

Gemini's protocol specification fits on a few pages. This simplicity is intentional:

- **One request per connection**: No persistent connections, no keep-alive, no pipelining
- **Simple request format**: Just a URL followed by CRLF (Carriage Return, Line Feed)
- **Limited status codes**: 20 status codes compared to HTTP's 60+
- **No content negotiation**: Server decides what to send
- **No cookies**: No tracking mechanisms built into the protocol
- **No client-side scripting**: No JavaScript, no dynamic execution

This constraint encourages focus on content rather than presentation or interactivity.

### Text-Centric Content

While Gemini can serve any file type, its native format is **gemtext** - a lightweight markup language even simpler than Markdown. Gemtext supports:

- Text paragraphs (no markup needed)
- Three levels of headings (`#`, `##`, `###`)
- Links (always on their own line, optionally with text)
- Unordered lists (`*` prefix)
- Preformatted blocks (code, ASCII art, etc.)
- Blockquotes (`>` prefix)

That's it. No inline formatting, no images embedded in text, no tables, no nested structures. This constraint makes gemtext trivial to parse and render, encouraging diverse client implementations.

## How Gemini Works

### Connection Model

Every Gemini transaction follows the same pattern:

1. Client opens TLS connection to server on port 1965
2. Client sends a single URL followed by `\r\n`
3. Server sends a status code, metadata, and optional body
4. Server closes the connection

This stateless, non-persistent model is reminiscent of HTTP/0.9 but with mandatory TLS. Each request requires a new connection, which trades some efficiency for simplicity and reduced server state.

### URL Scheme

Gemini URLs use the `gemini://` scheme:

```
gemini://example.com/path/to/content
```

The maximum request size is 1024 bytes, including the URL and CRLF terminator. This limit prevents abuse while being sufficient for legitimate use.

### Response Format

Server responses consist of:

- **Status code**: 2-digit code indicating success, redirect, error, etc.
- **Meta information**: MIME type (for success), redirect URL, or error message
- **Body**: Optional content (only for success responses)

Status codes are organized by first digit:

- **1x**: Input required from client
- **2x**: Success - content follows
- **3x**: Redirect
- **4x**: Temporary failure
- **5x**: Permanent failure
- **6x**: Client certificate required

### Client Certificates

Gemini supports **client certificates** for authentication and identity. This is handled through TLS, not through a separate authentication mechanism:

- Users can generate their own certificates (self-signed is normal)
- Servers can require certificates for specific paths
- Certificates enable persistent identity without usernames/passwords
- Users control their identity data, not servers

Since Gemini doesn't use traditional Certificate Authorities for client certs, users are in full control of their identity credentials.

## Trust On First Use (TOFU)

Instead of relying on Certificate Authorities like the Web does, Gemini clients typically use **Trust On First Use** (TOFU) for server certificate validation:

1. First connection to a host: Accept and remember the certificate
2. Subsequent connections: Verify the certificate matches what was seen before
3. Certificate change: Warn the user (could be legitimate renewal or an attack)

This approach:

- Eliminates the need for expensive CA certificates
- Removes centralized trust authorities from the equation
- Puts users in control of trust decisions
- Encourages self-hosted content

TOFU is similar to SSH's host key verification - slightly less convenient than implicit trust, but much more secure than ignoring certificates entirely.

## Why Choose Gemini?

### Privacy Benefits

- **No tracking by default**: No cookies, no local storage, no client-side execution
- **Encrypted always**: TLS is mandatory, never optional
- **Minimal metadata**: Simple protocol means less information leaked
- **User control**: TOFU puts trust decisions in users' hands

### Simplicity Benefits

- **Easy to implement**: Complete servers can be written in a few hundred lines
- **Accessible development**: No need to master complex web standards
- **Diverse clients**: Low barrier to entry encourages client diversity
- **Predictable behavior**: No JavaScript means content behaves the same everywhere

### Content Focus

- **No distractions**: Text-only format keeps focus on ideas, not presentation
- **Fast loading**: No ads, trackers, or heavy assets to download
- **Low bandwidth**: Gemtext is tiny compared to modern web pages
- **Accessibility**: Simple format is easy to render in any environment

### Sustainability

- **Low resource usage**: Simple protocol and lightweight content reduce energy consumption
- **Long-term stability**: Small specification is less likely to change
- **Independence**: Self-signed certificates and TOFU reduce external dependencies

## What Gemini Is Not

It's important to understand Gemini's limitations and intentional constraints:

- **Not a web replacement**: Gemini is deliberately limited and won't work for many web use cases
- **Not for applications**: No client-side code execution, no real-time interaction
- **Not multimedia-rich**: While you can serve images/video, gemtext itself is text-only
- **Not backwards-compatible**: Gemini sites require Gemini clients; web browsers won't work

These aren't bugs - they're features. Gemini is designed for a specific niche: thoughtful, text-centric content in a private, simple environment.

## The Gemini Ecosystem

Since its creation in 2019, Gemini has developed a small but active community:

- **Gemini servers**: Dozens of server implementations in various languages
- **Gemini clients**: Desktop browsers, terminal clients, mobile apps
- **Content**: Personal blogs, technical documentation, creative writing, community spaces
- **Aggregators**: Tools for discovering and following Gemini content

The community values experimentation, simplicity, and the "small web" ethos - personal expression over commercial presence.

## Official Resources

To learn more about Gemini and its community:

- **Project Gemini Home**: [geminiprotocol.net](https://geminiprotocol.net/) - Official project site and community hub
- **Gemini Specification**: [geminiprotocol.net/docs/specification.gmi](https://geminiprotocol.net/docs/specification.gmi) - Complete protocol specification
- **Gemtext Specification**: [geminiprotocol.net/docs/gemtext.gmi](https://geminiprotocol.net/docs/gemtext.gmi) - Gemtext markup format details
- **FAQ**: [geminiprotocol.net/docs/faq.gmi](https://geminiprotocol.net/docs/faq.gmi) - Frequently asked questions
- **Gemini Software**: [geminiprotocol.net/software/](https://geminiprotocol.net/software/) - Curated list of clients and servers

!!! note "Viewing Gemini Resources"
    The official Gemini documentation is published in gemtext format at `gemini://` URLs. To view these resources, you'll need a Gemini client. Web proxies like [portal.mozz.us](https://portal.mozz.us/) allow viewing Gemini content in a web browser.

## See Also

- [Getting Started with Nauyaca](../quickstart.md) - Build and use your first Gemini server
- [Gemtext Format Reference](../gemini_protocol/gemtext.txt) - Detailed gemtext syntax
- [Security Model](../explanation/security-model.md) - How Nauyaca implements TLS and TOFU
