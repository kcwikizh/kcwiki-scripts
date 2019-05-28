import logging
from .config import CONFIG
logging.basicConfig(
    filename=CONFIG['log'],
    format="%(levelname)-10s %(asctime)s %(message)s",
    level=logging.DEBUG
)
log = logging.getLogger('kcwiki-scripts')


def debug(msg, *args, **kwargs):
    if CONFIG['debug']:
        log.debug(msg, *args, **kwargs)