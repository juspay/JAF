import httpx
import gc
import os
import json

from jaf.logger import init_logger

logger = init_logger(__name__)

def run_gc(name):
    gc.collect()
    logger.debug("cleaning garbage from {name}")


def get_network_proxy(name):
    proxies = json.loads(os.getenv("OUTGOING_HTTP_PROXY", "null") )   # {"http":"", "https": ""}
    if proxies:
        logger.info(f"Using network proxy - {proxies} in {name}")
        return httpx.Client(proxies=proxies)

    return proxies
