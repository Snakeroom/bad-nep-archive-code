import logging
import os

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

if "DEBUG" in os.environ:
    logging.basicConfig(level=logging.DEBUG)
elif "NOLOG" not in os.environ:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("gql.transport.websockets").setLevel(level=logging.WARNING)

sentry_sdk.init(
    os.environ["SENTRY_DSN"],
    traces_sample_rate=0.01,
    integrations=[HttpxIntegration(), CeleryIntegration(), SqlalchemyIntegration()],
    ignore_errors=[KeyboardInterrupt],
)
