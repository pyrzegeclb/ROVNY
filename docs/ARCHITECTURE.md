# Architecture

The browser is a review surface. A loopback Python service owns project access, change validation and provider calls. The UI never receives provider API keys. The backend generates a per-launch capability token; every `/api` call requires it. Vite's same-origin proxy is only for development.

## Change lifecycle

1. Open a project. The service resolves its absolute directory and returns a workspace ID. Every project operation must carry that ID.
2. Select context explicitly. The backend reads selected files and captures hashes before awaiting a model response.
3. A provider adapter returns the common `Proposal` schema: a summary and complete replacement contents for 1–30 relative file paths. `null` means delete.
4. Existing files outside the selected context cannot be changed by an agent response. Paths, sizes and hashes are validated. Unified diffs are computed by Python and stored in an in-memory pending plan.
5. Apply rechecks every file hash under the workspace lock, persists a before-state snapshot, and replaces files via temporary files plus `os.replace`. Ordinary write errors trigger rollback of the entire batch. Process crashes or storage failures during rollback require manual snapshot recovery; this is not a journaled filesystem transaction.
6. Revert checks post-apply hashes and restores the before-state. Explicit snapshot restore captures a new backup first. Manual full snapshots restore the eligible file set; transaction snapshots restore only touched paths.

Each workspace has a reentrant lock. Requests for the same resolved project reuse its workspace. Model network waits happen outside this lock so reading remains available, then hashes are checked again. Terminal commands take the workspace lock and a global command lock. This does not lock out external editors or other OS processes.

## Providers

`providers.py` isolates native Ollama and OpenAI-compatible payloads. Add new adapters by extending the settings discriminator and `propose` dispatch while preserving `Proposal`. Remote access is disabled by default; arbitrary redirect following and environment proxy use are disabled. Provider output remains untrusted and cannot call terminal APIs.

## Persistence

- `backend/.state/settings.json`: non-secret provider preferences; overridable by `ROVNY_STATE_DIR`.
- `<project>/.rovny/<id>.json`: base64-encoded file bytes and snapshot metadata. These contain project content; protect them like source files.
- Plans and workspace handles: session memory. Restarting invalidates them.
- Browser session storage: token. Browser local storage: last project path only.

## Future work

Native folder selection / optional Electron wrapper, bounded iterative tool agent, persistent plan history, `.gitignore` integration, hardened filesystem operations against hostile concurrent writers, terminal process isolation, and richer editor navigation.

## Conversation mode (v0.2)

`ChatPanel` owns browser-local conversations, scoped to the project path or general chat. The Python `/api/chat` endpoint validates user/assistant history, reads only selected files, trims context, and streams provider text as NDJSON. Ollama NDJSON and OpenAI-compatible SSE are translated into common start/delta/done/error events. Aborting fetch closes the backend/provider stream. Partial/stopped assistant responses are not sent as completed history. Markdown renders without raw HTML or automatic remote images.

Plan mode passes the current request and bounded recent dialogue to the existing proposal endpoint. It still requires explicit Apply. Pending plan objects remain server-memory resources and are not restored from browser history after restart.
