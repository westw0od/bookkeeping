"""Local entry point with bounded logs, instead of unbounded redirected streams."""
import logging
import logging.config
import uvicorn
from runtime_logging import log_config

if __name__ == '__main__':
    config = log_config()
    logging.config.dictConfig(config)
    logging.captureWarnings(True)
    try:
        uvicorn.run('main:app', host='127.0.0.1', port=8000, log_config=config,
                    proxy_headers=True, forwarded_allow_ips='127.0.0.1')
    except Exception:
        logging.getLogger(__name__).exception('Local server failed to start')
        raise SystemExit(1)
