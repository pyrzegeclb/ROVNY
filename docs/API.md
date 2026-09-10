# API v0.2

Every request needs `Authorization: Bearer <session-token>`. Workspace operations additionally need `X-Workspace: <id>` returned by opening a project. Send JSON bodies with `Content-Type: application/json`.

| Method | Route | Purpose |
| --- | --- | --- |
| POST | `/api/projects` | `{ "path": "/absolute/folder" }` → id, path, name |
| GET | `/api/tree` | Eligible `{path,size}` file entries |
| GET | `/api/file?path=...` | UTF-8 content and SHA-256 hash |
| POST | `/api/edit` | `{path,content,hash}` → pending plan; null hash for new file |
| GET | `/api/search?q=...` | Up to 200 literal matches with path, line and text |
| GET / PUT | `/api/settings` | provider, endpoint, model, allow_remote |
| POST | `/api/agent` | `{prompt,files:["relative/path"]}` → pending plan |
| POST | `/api/plans/{id}/apply` | Apply pending plan after hash validation |
| POST | `/api/plans/{id}/revert` | Revert applied plan if unchanged |
| GET / POST | `/api/snapshots` | List / create manual full snapshot |
| POST | `/api/snapshots/{id}/restore` | Restore and return a recovery backup ID |
| POST | `/api/terminal` | `{argv:["git","status"],confirmed:true}` → output, exit_code, notice |

`content: null` is a deletion request. Plan objects contain a summary, status and changes with path, action, complete new contents, old hash and unified diff. Plan status is pending → applied → reverted. Regenerate after conflicts. Errors use `detail`. Invalid data is 400/422, missing authentication 401, forbidden origin/command 403, missing resource 404, busy terminal 409, provider failure 502.

Plans are scoped to a workspace and process lifetime. There is no unauthenticated health endpoint or public remote API. A model response is never interpreted as an API request.

## Streaming chat

`POST /api/chat` requires session authentication. A workspace header is optional when no files are attached. Body: `{ "messages": [{"role":"user","content":"Hello"}], "files": [] }`. Only user/assistant roles are accepted; the final message must be user. Maximum 40 input messages, 16,000 characters per message, 30 file paths. The service trims oldest history to a 24,000-character combined context budget and rejects oversized attachments before contacting the model.

The response is newline-delimited JSON: `start` (model, trimmed), `delta` (text), `done` (truncated), or `error` (text). Clients must parse complete lines across transport chunks, render deltas, and treat a connection closing without done as incomplete. Cancel by aborting the HTTP request; closing the stream releases the provider connection. Provider output length is bounded to 2,048 tokens for chat. Larger local models have a 600-second read timeout. Chat never calls workspace write or terminal operations.
