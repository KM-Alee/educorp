#!/usr/bin/env bash
# infra/temporal/init.sh
set -e

TEMPORAL_CLI="${TEMPORAL_CLI:-tctl}"
NAMESPACE="${TEMPORAL_NAMESPACE:-educorp}"

echo "Registering Temporal namespace: $NAMESPACE"
$TEMPORAL_CLI --ns "$NAMESPACE" namespace register \
    --retention 72h \
    --description "EduCorp publishing workflows" \
    || echo "Namespace ${NAMESPACE} already exists"
echo "Namespace $NAMESPACE ready"
