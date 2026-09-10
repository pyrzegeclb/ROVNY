# Security model

In v0.2, conversation messages are stored in this browser's local storage, separately by project path. Treat the browser profile like local source data. The latest project path is reopened on reload; file selections are not automatically restored or sent. Markdown messages do not execute raw HTML or automatically fetch external images. Chat reads only explicitly selected files and cannot call file-write or terminal APIs. Stop closes the request/provider stream; partial assistant output is marked and excluded from future conversation context.

ROVNY is for a single user working with trusted local projects. It is not a container, virtual machine or privilege boundary against a hostile local user/process.

## Enforced controls

- Backend binds `127.0.0.1:8765`; all API calls require a random startup token (or a user-provided `ROVNY_TOKEN`). Tokens are not API query parameters.
- Host and Origin checks reject unexpected browser callers; no wildcard CORS. Keep the default ports unless updating the allowlist deliberately.
- Relative project paths only; reject traversal, Windows drive/alternate-stream syntax, symlinks and junctions. `.git`, `.rovny`, `node_modules`, `.venv`, `__pycache__`, `dist`, `build`, `.env*`, `*.pem` and `*.key` are protected/excluded.
- Editing uses UTF-8 and rejects NUL-containing files. Snapshot bytes are base64 encoded and validated on restore. Restore paths go through the same project guard.
- Agent changes require a UI apply action. File hashes reject stale proposals and stale reverts. Plans cannot request shell execution.
- A terminal request must include explicit approval, uses argument arrays and no implicit shell, and is limited to 30 seconds / 1 MiB captured output. Provider and session keys are removed from the child environment. At most one command runs at a time.
- Remote provider endpoints require an explicit opt-in and HTTPS. Local providers need no account/key. No telemetry, remote fonts or CDNs are used by the UI.

## Boundaries and limitations

**Terminal execution has your normal OS permissions.** It can access files outside the workspace, the network and secrets inherited from your environment or stored on disk. Explicit shells (`cmd.exe /c`, `sh -c`) and interpreters remain possible. Run untrusted commands in a separate container/VM. Limits are best-effort polling; processes that detach may escape cleanup. This is a bounded command runner, not a sandbox or interactive terminal.

Secret filename filtering is not a secret scanner: private data can appear in ordinary source files, comments and prompts. Review selected context before enabling a remote model. Loopback services can themselves proxy to the cloud; ROVNY cannot attest to how a model server handles data.

Path checks protect routine requests, but do not eliminate filesystem race attacks by concurrent hostile writers. Do not open untrusted projects while another process is mutating their links. External tools can race the hash checks. Snapshots do not preserve ownership, extended attributes, original timestamps or empty directory topology. Rollback keeps newly created empty parent directories. Snapshots are plaintext-equivalent local backups, not encryption.

Manual full restore removes eligible files added after capture; it never touches excluded/protected files. Generated folders and secret files are not backed up. A full snapshot is not a replacement for Git or a system backup. Large trees fail explicitly instead of silently producing an incomplete full backup.

The Python server must not be reverse-proxied to the internet. Do not share the session URL. The app serves its static UI without authentication, but project content and API operations are authenticated. The service is single-process; do not run multiple workers sharing settings and snapshots.

For a vulnerability report, contact the repository maintainer privately; no reporting mailbox has been assigned in this initial scaffold. Do not publish credentials or exploit data in an issue.
