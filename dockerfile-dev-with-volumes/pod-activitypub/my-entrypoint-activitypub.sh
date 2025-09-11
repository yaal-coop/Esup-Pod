#!/bin/sh
watchmedo auto-restart --directory=/usr/src/app --pattern=*.py --recursive -- \
celery --app pod.activitypub.tasks worker --loglevel INFO --queues activitypub --concurrency 1 --hostname activitypub
sleep infinity
