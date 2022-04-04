#!/bin/sh
celery -A placedump.tasks worker -l INFO --autoscale 24,2