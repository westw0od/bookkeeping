"""Bounded local logs; no request bodies, credentials or query strings."""
import logging
import logging.config
import logging.handlers
import re
import time
from pathlib import Path

MAX_LOG_BYTES = 5 * 1024 * 1024
LOG_BACKUPS = 4
LOG_RETENTION_DAYS = 14
DEFAULT_LOG_DIR = Path(__file__).resolve().parents[1] / '.local' / 'logs'

class SafeLogFilter(logging.Filter):
    def filter(self, record):
        if record.name == 'uvicorn.access' and isinstance(record.args, tuple) and len(record.args) == 5:
            client, method, path, version, status = record.args
            if path.split('?', 1)[0] == '/api/health':
                return False
            record.args = (client, method, path.split('?', 1)[0], version, status)
        return True

class PrivateFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        message = re.sub(r'(?i)(Bearer\s+)\S+', r'\1[REDACTED]', message)
        message = re.sub(r'\bsk-[A-Za-z0-9_-]{8,}', '[REDACTED_KEY]', message)
        return message

def prune_logs(log_dir, now=None):
    root = Path(log_dir).resolve()
    if not root.exists():
        return 0
    cutoff = (time.time() if now is None else now) - LOG_RETENTION_DAYS * 86400
    removed = 0
    for item in root.iterdir():
        # Only our numbered rotations, never live logs, arbitrary files or links.
        if item.is_symlink() or not item.is_file() or not re.fullmatch(r'(app|access|tunnel)\.log\.\d+', item.name):
            continue
        try:
            if item.resolve().parent == root and item.stat().st_mtime < cutoff:
                item.unlink(); removed += 1
        except (FileNotFoundError, PermissionError):
            pass
    return removed

class BoundedLogHandler(logging.handlers.RotatingFileHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.next_prune = 0
    def emit(self, record):
        if time.time() >= self.next_prune:
            prune_logs(Path(self.baseFilename).parent)
            self.next_prune = time.time() + 86400
        super().emit(record)

def log_config(log_dir=DEFAULT_LOG_DIR):
    root = Path(log_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    prune_logs(root)
    def handler(name):
        return {'class': 'runtime_logging.BoundedLogHandler', 'filename': str(root / name),
                'maxBytes': MAX_LOG_BYTES, 'backupCount': LOG_BACKUPS, 'encoding': 'utf-8',
                'formatter': 'private', 'filters': ['safe']}
    return {'version': 1, 'disable_existing_loggers': False,
        'filters': {'safe': {'()': SafeLogFilter}},
        'formatters': {'private': {'()': PrivateFormatter, 'format': '%(asctime)s %(levelname)s %(name)s %(message)s'}},
        'handlers': {'app': handler('app.log'), 'access': handler('access.log')},
        'root': {'handlers': ['app'], 'level': 'INFO'},
        'loggers': {'uvicorn': {'handlers': ['app'], 'level': 'INFO', 'propagate': False},
                    'uvicorn.error': {'handlers': ['app'], 'level': 'INFO', 'propagate': False},
                    'uvicorn.access': {'handlers': ['access'], 'level': 'INFO', 'propagate': False},
                    'httpx': {'level': 'WARNING'}, 'httpcore': {'level': 'WARNING'}}}

def tunnel_logger():
    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    prune_logs(DEFAULT_LOG_DIR)
    logger = logging.getLogger('bookkeeping.tunnel')
    logger.setLevel(logging.INFO); logger.propagate = False
    handler = BoundedLogHandler(DEFAULT_LOG_DIR / 'tunnel.log', maxBytes=MAX_LOG_BYTES,
                                                   backupCount=LOG_BACKUPS, encoding='utf-8')
    handler.setFormatter(PrivateFormatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)
    return logger
