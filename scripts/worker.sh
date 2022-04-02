#!/bin/sh
celery -A placedump.tasks worker -l INFO --autoscale 8,2