#!/bin/bash
set -e

# Open Logistics Restore Script

BACKUP_FILE=${1}
NAMESPACE=${2:-openlogistics}

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file> [namespace]"
    echo "Example: $0 /backups/openlogistics_backup_20231201_120000.tar.gz"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[ERROR] Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "[RESTORE] Starting restore process from $BACKUP_FILE..."

# Extract backup
TEMP_DIR=$(mktemp -d)
tar -xzf $BACKUP_FILE -C $TEMP_DIR
BACKUP_DIR=$(find $TEMP_DIR -maxdepth 1 -type d -name "*[0-9]*" | head -1)

if [ -z "$BACKUP_DIR" ]; then
    echo "[ERROR] Invalid backup file structure"
    exit 1
fi

echo "[INFO] Backup manifest:"
cat $BACKUP_DIR/backup_manifest.json

read -p "Continue with restore? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled"
    exit 1
fi

# Scale down applications
echo "[SCALE] Scaling down applications..."
kubectl scale deployment/open-logistics --replicas=0 -n $NAMESPACE

# Restore PostgreSQL
echo "[DB] Restoring PostgreSQL database..."
kubectl exec -n $NAMESPACE deployment/postgres -- psql -U openlogistics -c "DROP DATABASE IF EXISTS openlogistics;"
kubectl exec -n $NAMESPACE deployment/postgres -- psql -U openlogistics -c "CREATE DATABASE openlogistics;"
kubectl exec -i -n $NAMESPACE deployment/postgres -- psql -U openlogistics openlogistics < $BACKUP_DIR/postgres_backup.sql

# Restore Redis
echo "[REDIS] Restoring Redis data..."
kubectl cp $BACKUP_DIR/redis_backup.rdb $NAMESPACE/$(kubectl get pods -n $NAMESPACE -l app=redis -o jsonpath='{.items[0].metadata.name}'):/data/dump.rdb
kubectl exec -n $NAMESPACE deployment/redis -- redis-cli FLUSHALL
kubectl exec -n $NAMESPACE deployment/redis -- redis-cli DEBUG RESTART

# Restore application data
echo "[DATA] Restoring application data..."
kubectl cp $BACKUP_DIR/app_data.tar.gz $NAMESPACE/$(kubectl get pods -n $NAMESPACE -l app=open-logistics -o jsonpath='{.items[0].metadata.name}'):/tmp/app_data.tar.gz
kubectl exec -n $NAMESPACE deployment/open-logistics -- tar -xzf /tmp/app_data.tar.gz -C /

# Scale up applications
echo "[SCALE] Scaling up applications..."
kubectl scale deployment/open-logistics --replicas=3 -n $NAMESPACE

# Wait for applications to be ready
echo "[WAIT] Waiting for applications to be ready..."
kubectl rollout status deployment/open-logistics -n $NAMESPACE --timeout=300s

# Verify restore
echo "[VERIFY] Verifying restore..."
kubectl exec -n $NAMESPACE deployment/open-logistics -- openlogistics version

# Cleanup
rm -rf $TEMP_DIR

echo "[SUCCESS] Restore completed successfully!"
