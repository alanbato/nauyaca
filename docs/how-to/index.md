# How-To Guides

How-to guides are practical, task-oriented instructions for solving specific problems. Unlike tutorials (which guide you through learning), these guides assume you're familiar with Nauyaca and focus on accomplishing particular tasks.

!!! tip "Looking to Learn?"
    If you're new to Nauyaca, start with the [Tutorials](../tutorials/index.md) section instead. How-to guides assume basic familiarity with the project.

## Available Guides

<div class="grid cards" markdown>

-   :material-cog: **Configure Server**

    ---

    Set up your Gemini server using TOML configuration files. Learn about all available options, defaults, and configuration patterns.

    [:octicons-arrow-right-24: Configuration Guide](configure-server.md)

-   :material-certificate: **Manage Certificates**

    ---

    Generate and manage TLS certificates for your server. Create self-signed certificates for development or prepare for production deployment.

    [:octicons-arrow-right-24: Certificate Management](manage-certificates.md)

-   :material-shield-check: **Setup TOFU**

    ---

    Configure Trust-On-First-Use (TOFU) certificate validation for secure client connections. Import, export, and manage trusted hosts.

    [:octicons-arrow-right-24: TOFU Setup](setup-tofu.md)

-   :material-speedometer: **Rate Limiting**

    ---

    Protect your server from DoS attacks with token bucket rate limiting. Configure per-IP limits and customize behavior.

    [:octicons-arrow-right-24: Rate Limiting Guide](rate-limiting.md)

-   :material-shield-lock: **Access Control**

    ---

    Implement IP-based access control with allow and deny lists. Use CIDR notation for network ranges and combine with rate limiting.

    [:octicons-arrow-right-24: Access Control Guide](access-control.md)

-   :material-account-key: **Client Certificates**

    ---

    Configure client certificate authentication for protected resources. Set up path-based certificate requirements and handle certificate validation.

    [:octicons-arrow-right-24: Client Certificates Guide](client-certificates.md)

-   :material-file-document-outline: **Logging**

    ---

    Configure logging and monitoring for your Gemini server. Set log levels, customize formats, and track server activity.

    [:octicons-arrow-right-24: Logging Guide](logging.md)

</div>

## Guide Structure

Each how-to guide follows this structure:

- **Problem statement**: What you want to accomplish
- **Prerequisites**: What you need before starting
- **Steps**: Clear, numbered instructions
- **Verification**: How to confirm it worked
- **Troubleshooting**: Common issues and solutions

## See Also

- **[Tutorials](../tutorials/index.md)**: Step-by-step learning paths for beginners
- **[Reference](../reference/index.md)**: Complete API and CLI documentation
- **[Explanation](../explanation/index.md)**: Conceptual topics and design decisions
