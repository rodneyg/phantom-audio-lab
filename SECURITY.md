# Security

Both commands use `127.0.0.1` only. They have no remote-host option and default to a separate lab port, `8799`. The receiver rejects browser Origin headers, validates frames, and bounds message size/queue depth.

This is an unencrypted local diagnostic, not an authenticated audio service. Other local processes can connect. Never expose it with a proxy, port forwarding, public interface, or tunnel. Never send private audio to it.

Report issues to maintainers using a synthetic reproduction. Do not post credentials or recordings. This lab has no access to product accounts or data and no private security reporting endpoint is configured yet.
