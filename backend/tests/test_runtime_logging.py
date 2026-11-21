import logging
import os
import time
from logging.handlers import RotatingFileHandler
from runtime_logging import PrivateFormatter, SafeLogFilter, prune_logs

def test_access_logs_omit_queries_and_health_checks():
    safe = SafeLogFilter()
    record = logging.LogRecord('uvicorn.access', logging.INFO, '', 0, '%s %s %s %s %s', ('client', 'GET', '/api/ledger?private=value', '1.1', 200), None)
    assert safe.filter(record)
    assert 'private' not in record.getMessage()
    record.args = ('client', 'GET', '/api/health', '1.1', 200)
    assert not safe.filter(record)

def test_bounded_rotations_and_age_cleanup_preserve_active_and_unknown_files(tmp_path):
    handler = RotatingFileHandler(tmp_path / 'app.log', maxBytes=100, backupCount=4, encoding='utf-8')
    handler.setFormatter(PrivateFormatter('%(message)s'))
    try:
        for _ in range(100):
            handler.emit(logging.LogRecord('test', logging.INFO, '', 0, 'line-' + 'x' * 45, (), None))
    finally:
        handler.close()
    assert len(list(tmp_path.glob('app.log*'))) == 5
    unknown = tmp_path / 'ledger-backup.json'; unknown.write_text('keep')
    ancient = time.time() - 15 * 86400
    for p in tmp_path.iterdir(): os.utime(p, (ancient, ancient))
    assert prune_logs(tmp_path) == 4
    assert (tmp_path / 'app.log').exists() and unknown.exists()
    formatted = PrivateFormatter().format(logging.LogRecord('test', logging.INFO, '', 0, 'Bearer token-value sk-not-a-real-key-123456', (), None))
    assert 'token-value' not in formatted and 'sk-not-a-real-key' not in formatted
