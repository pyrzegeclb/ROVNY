# Local performance update

Ollama calls now default to num_ctx=4096, think=false and streaming. Settings can change the context limit. The Windows Ollama launcher enables Flash Attention, q8_0 KV cache and one parallel request. The machine-specific launcher also keeps a 512 MiB fit target; this runtime-specific setting increased offload from 7/41 to 10/41 layers on the MX570 A.

The ROVNY heading shows an updating approximate rate during chat (Unicode characters / 4 / elapsed time). It is not an exact tokenizer count or instantaneous hardware measurement. Completion replaces it with Ollama eval_count / eval_duration. Hover for first-content latency and prompt evaluation speed. Plan mode shows final metrics only.

Content-free completed request metrics are written to backend/.state/performance.jsonl, rotated at 5 MiB. Compatible endpoints may not provide token counts. Run backend/benchmark.py --label comparison --ctx 4096 --output results.jsonl to compare fixed public prompts; warmup is recorded separately. Prompt cache counts and uncached throughput are reported when available. These short correctness probes do not establish general model quality.

Before the user requested tests stop, the same short first-pass prompts measured 7.73-7.76 tokens/s at 8192 context and 8.09-8.16 with 4096, Flash Attention, q8_0 and 512 MiB fit margin. Q4_K_S required the official model template to honor think=false; it remains an optional experimental model. Qwen3 14B Q4_K_M remains selected. No 10-12 or 40+ tokens/s result is claimed. No further tests were run after the stop request.

References: https://docs.ollama.com/faq and https://docs.ollama.com/api/chat
