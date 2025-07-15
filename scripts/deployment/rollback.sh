#!/bin/bash
set -e

# Open Logistics Rollback Script

ENVIRONMENT=${1:-development}
NAMESPACE=${2:-openlogistics}
REVISION=${3:-}

echo "🔄 Rolling back Open Logistics in $ENVIRONMENT environment..."

if [ -z "$REVISION" ]; then
    echo "📋 Available revisions:"
    kubectl rollout history deployment/open-logistics -n $NAMESPACE
    echo "Please specify a revision number as the third argument"
    exit 1
fi

# Perform rollback
echo "⏪ Rolling back to revision $REVISION..."
kubectl rollout undo deployment/open-logistics -n $NAMESPACE --to-revision=$REVISION

# Wait for rollback
echo "⏳ Waiting for rollback to complete..."
kubectl rollout status deployment/open-logistics -n $NAMESPACE --timeout=300s

# Verify rollback
echo "🔍 Verifying rollback..."
kubectl get pods -n $NAMESPACE -l app=open-logistics

echo "✅ Rollback completed successfully!"
