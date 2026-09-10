param([string]$Ollama = 'ollama', [string]$ModelDirectory = '')
$ErrorActionPreference = 'Stop'
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_FLASH_ATTENTION = '1'
$env:OLLAMA_KV_CACHE_TYPE = 'q8_0'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_CONTEXT_LENGTH = '4096'
if ($ModelDirectory) { $env:OLLAMA_MODELS = $ModelDirectory }
& $Ollama serve
