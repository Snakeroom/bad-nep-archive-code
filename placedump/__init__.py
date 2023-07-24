import asyncio
import logging
import os

import sentry_sdk
import uvloop
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

debug = False

if "DEBUG" in os.environ:
    logging.basicConfig(level=logging.DEBUG)
    debug = True
elif "NOLOG" not in os.environ:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("gql.transport.websockets").setLevel(level=logging.WARNING)
    logging.getLogger("pottery").setLevel(level=logging.WARNING)

sentry_sdk.init(
    os.environ["SENTRY_DSN"],
    traces_sample_rate=0.01,
    integrations=[
        AsyncioIntegration(),
        HttpxIntegration(),
        CeleryIntegration(),
        SqlalchemyIntegration(),
        RedisIntegration(),
    ],
    ignore_errors=[KeyboardInterrupt],
    attach_stacktrace=True,
    send_default_pii=True,
    debug=debug,
)

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
