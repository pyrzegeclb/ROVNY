# ROVNY Harness

**Your code. Your model. Your workspace.**

ROVNY is an open-source, local-first AI coding workspace. React + TypeScript frontend, Python + FastAPI backend. Runs in your browser on localhost; no Tauri, Electron, account, telemetry, or cloud service required. Version **0.2.0**.

[Türkçe hızlı başlangıç](README.tr.md)

## Quick start

Requirements: **Python 3.11+**, **Node.js 22.12+**, npm. Initial dependency installation requires internet. After installation the app can run offline with a downloaded local model, or in Demo mode. Python must be available as `python` (use `python3` on systems that require it).

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm ci
npm run build
cd ..\backend
..\.venv\Scripts\python.exe -m rovny
```

### macOS / Linux

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cd frontend
npm ci
npm run build
cd ../backend
../.venv/bin/python -m rovny
```

Open the **localhost URL printed by the backend**. It contains a private session token in the URL fragment. The UI stores it in session storage and immediately removes it from the address bar. The backend serves the built UI on **127.0.0.1:8765**. Stop with Ctrl+C.

Alternatively, after setup, use `scripts/start.ps1` or `scripts/start.sh` from the repository root. Copy `.env.example` to `.env` only if you need optional environment settings.

## Chat workspace (new in v0.2)

The app opens in a full-width conversation view. **Sohbet** supports normal chat without opening a project, multi-turn context, streaming Markdown/code responses, copy and stop controls. Enter sends; Shift+Enter adds a line. Use **Yeni sohbet** to start another conversation. The latest 20 conversations and 80 messages each are stored in this browser, separately for each project path and general chat. Only the recent history fitting the context budget is sent to the provider; the UI displays a notice when earlier turns are omitted. Interrupted responses are excluded from future assistant context.

Choose **Plan** in the composer to turn a request and recent conversation into a reviewed file proposal. Open a project and select files for edits. Click a file or **Editörü göster** to show the editor alongside chat; **Sohbeti genişlet** returns to the wide conversation view. Chat itself does not write files or run commands.

The default model is **Qwen3 14B** (about 9.3 GB download), configurable in Settings. Run `ollama pull qwen3:14b`. Local inference memory use exceeds model download size; limited GPU memory means CPU offloading and slower output. Ollama thinking is disabled for direct answers. Smaller installed models remain selectable by model name.

Conversation text is persisted in browser local storage. It is not included in exported ZIPs or workspace snapshots. No remote Markdown images are loaded automatically. Chat attachment plus history budgets are bounded; large selected files require a smaller selection.

## First five minutes

1. Click **Open project** and paste an absolute folder path. The session token is filled from the startup URL. This version uses a path input, not a native folder picker.
2. Open **Settings** in the left rail. Choose **Demo** for a model-free smoke test, or configure a local model below. Click **Save settings**.
3. Check files in Explorer to include them in the model context. File contents are never automatically sent just because a folder is open.
4. Enter a request and click the arrow. Review the plan and file diffs. **Apply** saves a recovery snapshot and writes the changes. **Revert** restores the exact previous bytes if files have not changed since apply.
5. The editor's **Preview save** follows the same review flow. Use Explorer's new-file button to create a file; saving also goes through a plan. Search is a literal, case-insensitive content search; press Enter.
6. Open **Snapshots** to capture or restore the workspace. Open **Terminal** to run a reviewed argument array with an explicit approval checkbox.

Demo mode is deterministic and creates `ROVNY_DEMO.md`. It does not pretend to call an AI model. If that file already exists, select it as context before another demo request.

## Local model providers

### Ollama (no key)

Install [Ollama](https://ollama.com), then download a model, for example:

```sh
ollama pull qwen2.5-coder:7b
ollama serve
```

If Ollama is already running, a second `serve` is unnecessary. In ROVNY choose **Ollama**, endpoint `http://127.0.0.1:11434`, model `qwen2.5-coder:7b` (or your installed coding model). Hardware requirements depend on the model. The adapter uses the [Ollama chat API](https://docs.ollama.com/api/chat) with a JSON schema and a 600-second read timeout.

### OpenAI-compatible local endpoint (no key)

Start a compatible model server such as LM Studio or llama.cpp. Select **OpenAI-compatible**, set its base URL including `/v1` (for example `http://127.0.0.1:1234/v1`), and enter its model ID. The adapter calls `/chat/completions` using `response_format: {"type":"json_object"}`. The server must support this format. No API key is sent unless `ROVNY_API_KEY` is configured.

### Remote provider (optional)

Explicitly enable **Allow remote HTTPS endpoints**, use an HTTPS `/v1` base URL and model ID, and set `ROVNY_API_KEY` in `.env` if required. Restart the backend after changing environment variables. Your prompt and selected files are sent to that provider; keys stay in the backend environment. Provider settings are saved in `backend/.state/settings.json` and contain no API keys. Compatibility means the chat-completions JSON interface, not every vendor's proprietary API.

## Features

- Open local projects; expandable file tree; UTF-8 editor; create, modify and delete through plans.
- Literal content search with file/line matches (click opens the file).
- Explicit file context, model-independent proposal schema and human-reviewed multi-file diffs.
- Stale-file conflict checks before apply and revert; byte-preserving snapshots; recovery backup before restore.
- Terminal command runner with explicit confirmation, working directory, exit code, combined output and execution limits.
- Saved provider settings; local-only default; session authentication and origin/host validation.
- A complete offline Demo workflow, API tests, provider contract tests and CI.

## Development

Start the backend as above, then in another terminal:

```sh
cd frontend
npm run dev
```

Use the **Development UI** URL printed by the backend (port 5173). Vite proxies `/api` to the Python service; the production build is served by FastAPI. The dev server binds only to loopback. See [Vite](https://vite.dev/guide/) for its build workflow.

```sh
# From backend, with the repository venv's Python:
python -m pytest -q
# From frontend:
npm run build
```

## Repository layout

```text
backend/
  rovny/          HTTP API, workspace transactions, model adapters, command runner
  tests/          filesystem, API, provider and process behavior tests
frontend/
  src/components/ file tree, review panel, settings, terminal
  src/            application state, API client, types, styling
docs/             architecture, security, API and release notes
examples/         small project for the first run
scripts/          startup helpers
.github/          CI and issue templates
```

## Practical limits

This is a usable local v0.2, not an OS sandbox or a fully autonomous coding system. The Plan agent produces one proposal per request; it does not execute tools, iterate on tests, or auto-apply. No native desktop package, interactive PTY, language server, syntax highlighting, arbitrary unified-diff import, Git integration UI, or persisted plan history is included. Pending plans are in memory; snapshots persist in the project's `.rovny/` directory.

Text editing is limited to UTF-8 files of 1 MiB each, 30 changes per plan and 120 KB of explicit model context. Full snapshots are limited to 50 MiB. Projects containing more than 10,000 eligible files cannot be fully snapshotted; reduce scope. Secret-like paths, symlinks, junctions and generated directories are excluded. Custom `.gitignore` patterns are not interpreted. See [security](docs/SECURITY.md) before working with untrusted repositories or commands.

## License and contributions

[MIT](LICENSE). Contributions welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). Report reproducible bugs with OS, Python/Node versions and redacted steps; never include tokens, keys or private source code.
