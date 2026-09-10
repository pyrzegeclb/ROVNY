# Contributing

Use Python 3.11+ and Node 22.12+. Follow README setup, run backend tests and frontend build before submitting a change. Keep provider integrations behind the shared proposal contract. Prefer small changes with reproducible behavior descriptions.

Security-sensitive code needs tests for failure paths: traversal, symlinks, stale hashes, partial writes, recovery and authorization. Do not add autonomous command execution or automatic apply without an explicit product/security design review.

No real provider keys, model downloads, project data or machine-specific paths should be committed. Report UI issues with screenshots only after redacting code and session tokens. MIT contributions are assumed to be licensed under the repository license.
