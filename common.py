import logging


class Logger:
    def log_error(self, message):
        logging.error(message)

    def log_info(self, message):
        logging.info(message)
