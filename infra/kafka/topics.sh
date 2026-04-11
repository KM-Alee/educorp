#!/usr/bin/env bash
# infra/kafka/topics.sh
# Create Kafka topics with proper configuration
set -e

BOOTSTRAP_SERVER="${KAFKA_BOOTSTRAP_SERVER:-kafka:29092}"

topics=(
    "user.lifecycle:6:1"
    "course.lifecycle:12:1"
    "enrollment.lifecycle:12:1"
    "progress.lifecycle:12:1"
    "ai.usage:6:1"
    "notification.requests:6:1"
    # Dead letter queues
    "user.lifecycle.dlq:3:1"
    "course.lifecycle.dlq:3:1"
    "enrollment.lifecycle.dlq:3:1"
    "progress.lifecycle.dlq:3:1"
    "ai.usage.dlq:3:1"
    "notification.requests.dlq:3:1"
)

for topic_config in "${topics[@]}"; do
    IFS=':' read -r topic partitions replication <<< "$topic_config"
    kafka-topics --create \
        --bootstrap-server "$BOOTSTRAP_SERVER" \
        --topic "$topic" \
        --partitions "$partitions" \
        --replication-factor "$replication" \
        --if-not-exists
    echo "Created topic: $topic (partitions=$partitions, replication=$replication)"
done

echo "All topics created."
kafka-topics --list --bootstrap-server "$BOOTSTRAP_SERVER"
