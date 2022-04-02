import os
from datetime import timedelta

from celery import Celery

app = Celery("placedump")
redis_url = os.environ.get("REDIS_DATA_URL", "redis://localhost:6379/3")
cache_redis_url = os.environ.get("REDIS_CACHE_URL", "redis://localhost:6379/3")

app.conf.timezone = "UTC"
app.conf.broker_url = redis_url
app.conf.result_backend = cache_redis_url
app.conf.broker_transport_options = {"visibility_timeout": 3600}
app.conf.task_store_errors_even_if_ignored = True
app.conf.result_expires = timedelta(hours=1)

# Setup queues
app.conf.broker_transport_options = {
    "queue_order_strategy": "priority",
}

# Send task events for monitoring.
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True

# Use Pickle. It is awful but...
app.conf.task_serializer = "pickle"
app.conf.result_serializer = "pickle"
app.conf.accept_content = ["application/json", "application/x-python-serialize"]

import placedump.tasks.pixels
