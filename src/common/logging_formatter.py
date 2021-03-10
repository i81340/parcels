# import logging
#
# class RequestFormatter(logging.Formatter):
#     def format(self, record):
#         record.url = None
#         record.remote_addr = None
#         return super().format(record)
#
#
# formatter = RequestFormatter("[%(asctime)s] in [%(pathname)s:%(lineno)d] - message=%(message)s")
#
#
import logging, logging.handlers
from logging import StreamHandler, Formatter

def get_configured_logger(name):

    logger = logging.getLogger(name)

    if len(logger.handlers) == 0:
        FORMAT = "%(thread)s - %(asctime)s - %(levelname)s - %(pathname)s:%(lineno)d - %(message)s"
        formatter = logging.Formatter(fmt=FORMAT)
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger


