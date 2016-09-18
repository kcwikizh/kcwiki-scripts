import logging
from .config import config
logging.basicConfig(
    filename=config['log'],
    format="%(levelname)-10s %(asctime)s %(message)s",
    level=logging.DEBUG
)
log = logging.getLogger('kcwiki-scripts')


def debug(msg, *args, **kwargs):
    if config['debug']:
        log.debug(msg, *args, **kwargs)