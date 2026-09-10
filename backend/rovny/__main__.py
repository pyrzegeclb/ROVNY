from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / '.env')
import uvicorn
from .app import app, TOKEN

print('\nROVNY v0.2 — local session\n')
print('Open: http://127.0.0.1:8765/#token=' + TOKEN)
print('Development UI: http://127.0.0.1:5173/#token=' + TOKEN)
print('Keep this session token private. Press Ctrl+C to stop.\n')
uvicorn.run(app, host='127.0.0.1', port=8765, access_log=False)
