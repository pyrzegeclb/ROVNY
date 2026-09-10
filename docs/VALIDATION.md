# v0.2 validation — 2026-09-10

**36 tests passed, 1 skipped.** Strict TypeScript checking and the Vite production build passed (about 420 KB JS / 129 KB gzip). The skipped test still requires Windows symlink privileges. Two upstream test-client deprecation warnings remain. npm reported zero vulnerabilities when Markdown dependencies were installed.

New automated checks cover chat authentication, role validation, selected-file isolation, optional workspace behavior, multi-turn context, context trimming, oversized attachments, Ollama NDJSON, compatible-provider SSE and error events.

**Real model:** official Ollama 0.34.0 plus `qwen3:14b`, a 9.3 GB Q4_K_M model. The machine has about 64 GB RAM and an NVIDIA MX570 A with 4 GB VRAM. Ollama reported 79%/21% CPU/GPU execution at 8192-token context. Observed short-request generation rates were about 2.7–6.3 tokens/second; rates are workload dependent. No API key was used; endpoint is loopback and Ollama cloud features are disabled. The earlier 986 MB model remains as a faster fallback.

Actual browser checks passed: Turkish chat without a project; follow-up recall of the previous name and app idea; incremental response rendering; Stop preserving a marked partial answer; Qwen3 Plan mode producing a valid selected-file proposal; reload restoring the saved conversation and open project while resetting file attachments. The Qwen3 test requested a default value already present in the example at that point, so its valid proposal had no text diff. Earlier v0.1 tests exercised real edits/apply/revert. The desktop layout was visually checked at roughly 1330×910.

The v0.2 ZIP includes source and built frontend, excluding model weights/runtime binaries, browser history, user-created example files, private settings, snapshots, virtual environments and installed dependencies. Plans can be switched between conversations in the current UI session, but plan controls do not survive page reload; applied changes retain durable snapshots. Hosted CI and mobile behavior have not been verified.

# Historical v0.1 build validation

Validated on Windows on 2026-09-10 using Python 3.12 and Node.js 24.20.0.

## Results

- **Backend: 28 passed, 1 skipped.** The skipped test creates an OS symlink; this Windows session lacks the required privilege. Two dependency deprecation warnings from the Starlette/httpx test client are present; they do not fail tests.
- **Frontend: TypeScript strict checking and Vite production build passed.** Vite 6.4.3; production JS approximately 250 KB (77 KB gzip), CSS approximately 12 KB (3.5 KB gzip).
- **npm installation audit: 0 vulnerabilities reported** at installation time. This is not a guarantee against future advisories.
- **Live browser smoke test:** opened `examples/hello-project`; saved Demo provider settings; generated a pending proposal; applied it; opened its real content in the editor; reverted it and observed the file disappear; searched `Hello` and saw README/Python line matches; created a manual snapshot; ran `greeting.py` with explicit approval and observed `Hello, ROVNY!` / exit code 0.
- The rendered desktop UI was visually inspected at 1280×720. Responsive CSS is included; mobile and other desktop OS behavior were not manually verified.

## Automated coverage

Traversal and protected paths; snapshot path tampering; create/modify/delete transactions; preservation of CRLF bytes; stale apply/revert rejection; full restore and recovery; simulated mid-batch write failure with rollback; missing terminal newline diff formatting; API token/host/origin rejection; literal search; explicit terminal approval; output size bound; private token removal from child environment; agent context isolation and stale-context rejection; Ollama and OpenAI-compatible request/response contracts; invalid proposal schema rejection; remote-provider opt-in.

Provider transport tests use `httpx.MockTransport`. **No real LLM inference was run**: Ollama was not installed in this environment. Demo mode exercises the actual preview/apply/revert filesystem workflow, but cannot validate model quality, hardware fit, model availability or a third-party server's JSON support.

## Reproduce

Install `backend/requirements-lock.txt` for the exact Python versions used here. `backend/requirements.txt` contains supported version ranges. `frontend/package-lock.json` records npm dependencies; use `npm ci`.

Run backend `python -m pytest -q` and frontend `npm run build`. CI is configured for Windows/Linux backend checks and Linux frontend build; hosted CI has not been executed because this project has not been published to GitHub.

The ZIP includes source plus the built frontend. It omits `.venv`, `node_modules`, `.state`, `.rovny`, caches and private `.env` files. No provider credentials or fixed test-session token are included.
