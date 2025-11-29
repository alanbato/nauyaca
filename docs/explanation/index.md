# Explanation

This section provides background and context to deepen your understanding of Nauyaca and the Gemini protocol. While tutorials teach you how to use Nauyaca and references describe what it does, these explanations illuminate the "why" behind design decisions, protocols, and architectures.

## Purpose of This Section

Explanation documentation helps you:

- Understand the principles behind Nauyaca's architecture
- Make informed decisions about how to use the library
- Troubleshoot issues by understanding underlying mechanisms
- Evaluate whether Nauyaca is right for your use case

## Topics

<div class="grid cards" markdown>

-   :material-protocol:{ .lg .middle } __Gemini Protocol__

    ---

    Learn about the Gemini protocol specification, its design philosophy, and how it differs from HTTP. Understand the simplicity that makes Gemini unique.

    [:octicons-arrow-right-24: Learn about Gemini](gemini-protocol.md)

-   :material-sitemap:{ .lg .middle } __Architecture__

    ---

    Explore how Nauyaca is designed using Python's asyncio Protocol/Transport pattern. Understand the module structure and core design decisions.

    [:octicons-arrow-right-24: Explore architecture](architecture.md)

-   :material-shield-lock:{ .lg .middle } __Security Model__

    ---

    Understand Nauyaca's security approach, including TOFU (Trust On First Use) validation, rate limiting, and other protective measures.

    [:octicons-arrow-right-24: Understand security](security-model.md)

</div>

## How to Use This Section

These explanations are most valuable when:

- **Getting started**: Read the Gemini Protocol overview to understand what you're working with
- **Going deeper**: After completing tutorials, understand the architecture to use Nauyaca effectively
- **Troubleshooting**: Security model explanations help diagnose certificate or rate limiting issues
- **Contributing**: Architecture knowledge is essential for making informed contributions

!!! tip "Complement with Other Sections"
    Explanations work best alongside other documentation types:

    - Start with [Tutorials](../tutorials/index.md) to learn hands-on
    - Use [How-to Guides](../how-to/index.md) for specific tasks
    - Consult [Reference](../reference/index.md) for detailed API information
