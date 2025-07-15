#!/bin/bash

# OpenLogistics Backup Script
# Author: Nik Jois <nikjois@llamasearch.ai>
# Comprehensive backup solution for OpenLogistics platform

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="${1:-open-logistics}"
BACKUP_DIR="${BACKUP_DIR:-/tmp/openlogistics-backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="openlogistics_backup_${TIMESTAMP}"
RETENTION_DAYS=7

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking backup prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not available"
        exit 1
    fi
    
    # Check namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace $NAMESPACE does not exist"
        exit 1
    fi
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
    
    log_success "Prerequisites checked"
}

backup_kubernetes_resources() {
    log_info "Backing up Kubernetes resources..."
    
    local k8s_backup_dir="$BACKUP_DIR/$BACKUP_NAME/kubernetes"
    mkdir -p "$k8s_backup_dir"
    
    # Backup all resources in namespace
    kubectl get all -n "$NAMESPACE" -o yaml > "$k8s_backup_dir/all-resources.yaml"
    
    # Backup specific resource types
    local resource_types=(
        "configmaps"
        "secrets"
        "persistentvolumeclaims"
        "services"
        "deployments"
        "statefulsets"
        "daemonsets"
        "ingresses"
        "networkpolicies"
        "serviceaccounts"
        "roles"
        "rolebindings"
    )
    
    for resource in "${resource_types[@]}"; do
        if kubectl get "$resource" -n "$NAMESPACE" &> /dev/null; then
            kubectl get "$resource" -n "$NAMESPACE" -o yaml > "$k8s_backup_dir/$resource.yaml"
            log_success "Backed up $resource"
        fi
    done
    
    # Backup custom resources
    kubectl get crd -o yaml > "$k8s_backup_dir/custom-resource-definitions.yaml"
    
    log_success "Kubernetes resources backed up"
}

backup_database() {
    log_info "Backing up databases..."
    
    local db_backup_dir="$BACKUP_DIR/$BACKUP_NAME/database"
    mkdir -p "$db_backup_dir"
    
    # Backup PostgreSQL
    if kubectl get pod -l app=postgres -n "$NAMESPACE" &> /dev/null; then
        log_info "Backing up PostgreSQL..."
        
        local postgres_pod=$(kubectl get pod -l app=postgres -n "$NAMESPACE" -o jsonpath='{.items[0].metadata.name}')
        
        # Create PostgreSQL dump
        kubectl exec -n "$NAMESPACE" "$postgres_pod" -- pg_dump -U openlogistics openlogistics > "$db_backup_dir/postgresql_dump.sql"
        
        # Backup PostgreSQL configuration
        kubectl exec -n "$NAMESPACE" "$postgres_pod" -- cat /var/lib/postgresql/data/postgresql.conf > "$db_backup_dir/postgresql.conf"
        
        log_success "PostgreSQL backed up"
    else
        log_warning "PostgreSQL not found - skipping database backup"
    fi
    
    # Backup Redis
    if kubectl get pod -l app=redis -n "$NAMESPACE" &> /dev/null; then
        log_info "Backing up Redis..."
        
        local redis_pod=$(kubectl get pod -l app=redis -n "$NAMESPACE" -o jsonpath='{.items[0].metadata.name}')
        
        # Create Redis dump
        kubectl exec -n "$NAMESPACE" "$redis_pod" -- redis-cli BGSAVE
        sleep 5  # Wait for background save to complete
        kubectl cp -n "$NAMESPACE" "$redis_pod:/data/dump.rdb" "$db_backup_dir/redis_dump.rdb"
        
        log_success "Redis backed up"
    else
        log_warning "Redis not found - skipping Redis backup"
    fi
}

backup_persistent_volumes() {
    log_info "Backing up persistent volumes..."
    
    local pv_backup_dir="$BACKUP_DIR/$BACKUP_NAME/persistent-volumes"
    mkdir -p "$pv_backup_dir"
    
    # Get all PVCs in namespace
    local pvcs=$(kubectl get pvc -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')
    
    for pvc in $pvcs; do
        log_info "Backing up PVC: $pvc"
        
        # Get PVC details
        kubectl get pvc "$pvc" -n "$NAMESPACE" -o yaml > "$pv_backup_dir/$pvc.yaml"
        
        # Create a backup pod to copy data
        local backup_pod="backup-$pvc-$TIMESTAMP"
        
        cat << EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: $backup_pod
  namespace: $NAMESPACE
spec:
  containers:
  - name: backup
    image: busybox
    command: ['sleep', '3600']
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
    persistentVolumeClaim:
      claimName: $pvc
  restartPolicy: Never
EOF
        
        # Wait for pod to be ready
        kubectl wait --for=condition=ready pod "$backup_pod" -n "$NAMESPACE" --timeout=300s
        
        # Copy data from PVC
        kubectl exec -n "$NAMESPACE" "$backup_pod" -- tar czf - /data | gzip > "$pv_backup_dir/$pvc.tar.gz"
        
        # Cleanup backup pod
        kubectl delete pod "$backup_pod" -n "$NAMESPACE"
        
        log_success "PVC $pvc backed up"
    done
}

backup_application_data() {
    log_info "Backing up application data..."
    
    local app_backup_dir="$BACKUP_DIR/$BACKUP_NAME/application"
    mkdir -p "$app_backup_dir"
    
    # Backup application logs
    if kubectl get pods -l app=open-logistics -n "$NAMESPACE" &> /dev/null; then
        local app_pods=$(kubectl get pods -l app=open-logistics -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')
        
        for pod in $app_pods; do
            log_info "Backing up logs from pod: $pod"
            kubectl logs "$pod" -n "$NAMESPACE" > "$app_backup_dir/$pod.log"
        done
        
        log_success "Application logs backed up"
    fi
    
    # Backup configuration files
    kubectl get configmaps -n "$NAMESPACE" -o yaml > "$app_backup_dir/configmaps.yaml"
    kubectl get secrets -n "$NAMESPACE" -o yaml > "$app_backup_dir/secrets.yaml"
    
    log_success "Application data backed up"
}

backup_monitoring_data() {
    log_info "Backing up monitoring data..."
    
    local monitoring_backup_dir="$BACKUP_DIR/$BACKUP_NAME/monitoring"
    mkdir -p "$monitoring_backup_dir"
    
    # Backup Prometheus data
    if kubectl get pod -l app=prometheus -n "$NAMESPACE" &> /dev/null; then
        local prometheus_pod=$(kubectl get pod -l app=prometheus -n "$NAMESPACE" -o jsonpath='{.items[0].metadata.name}')
        
        # Backup Prometheus configuration
        kubectl exec -n "$NAMESPACE" "$prometheus_pod" -- cat /etc/prometheus/prometheus.yml > "$monitoring_backup_dir/prometheus.yml"
        
        # Backup Prometheus rules
        kubectl exec -n "$NAMESPACE" "$prometheus_pod" -- find /etc/prometheus/rules -name "*.yml" -exec cat {} \; > "$monitoring_backup_dir/prometheus-rules.yml"
        
        log_success "Prometheus configuration backed up"
    fi
    
    # Backup Grafana data
    if kubectl get pod -l app=grafana -n "$NAMESPACE" &> /dev/null; then
        local grafana_pod=$(kubectl get pod -l app=grafana -n "$NAMESPACE" -o jsonpath='{.items[0].metadata.name}')
        
        # Backup Grafana dashboards
        kubectl exec -n "$NAMESPACE" "$grafana_pod" -- find /var/lib/grafana/dashboards -name "*.json" -exec cat {} \; > "$monitoring_backup_dir/grafana-dashboards.json"
        
        log_success "Grafana dashboards backed up"
    fi
}

create_backup_archive() {
    log_info "Creating backup archive..."
    
    cd "$BACKUP_DIR"
    tar czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME/"
    
    # Remove uncompressed backup directory
    rm -rf "$BACKUP_NAME"
    
    log_success "Backup archive created: $BACKUP_DIR/$BACKUP_NAME.tar.gz"
}

cleanup_old_backups() {
    log_info "Cleaning up old backups..."
    
    # Remove backups older than retention period
    find "$BACKUP_DIR" -name "openlogistics_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
    
    log_success "Old backups cleaned up (retention: $RETENTION_DAYS days)"
}

verify_backup() {
    log_info "Verifying backup integrity..."
    
    # Check if backup file exists and is not empty
    if [ -f "$BACKUP_DIR/$BACKUP_NAME.tar.gz" ] && [ -s "$BACKUP_DIR/$BACKUP_NAME.tar.gz" ]; then
        # Test archive integrity
        if tar tzf "$BACKUP_DIR/$BACKUP_NAME.tar.gz" > /dev/null 2>&1; then
            log_success "Backup archive is valid"
            return 0
        else
            log_error "Backup archive is corrupted"
            return 1
        fi
    else
        log_error "Backup file does not exist or is empty"
        return 1
    fi
}

generate_backup_report() {
    log_info "Generating backup report..."
    
    local backup_size=$(du -h "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)
    
    cat > "$BACKUP_DIR/BACKUP_REPORT_$TIMESTAMP.md" << EOF
# OpenLogistics Backup Report

## Backup Information
- **Backup Name**: $BACKUP_NAME
- **Timestamp**: $(date)
- **Namespace**: $NAMESPACE
- **Backup Size**: $backup_size
- **Backup Location**: $BACKUP_DIR/$BACKUP_NAME.tar.gz
- **Created By**: $(whoami)

## Backup Contents
- [x] Kubernetes resources
- [x] Database dumps (PostgreSQL, Redis)
- [x] Persistent volume data
- [x] Application logs and configuration
- [x] Monitoring configuration

## Backup Verification
- [x] Archive integrity verified
- [x] File size check passed
- [x] Backup completion confirmed

## Restore Instructions
To restore from this backup:
\`\`\`bash
# Extract backup
tar xzf $BACKUP_NAME.tar.gz

# Restore Kubernetes resources
kubectl apply -f $BACKUP_NAME/kubernetes/

# Restore database (if needed)
kubectl exec -n $NAMESPACE <postgres-pod> -- psql -U openlogistics openlogistics < $BACKUP_NAME/database/postgresql_dump.sql

# Restore Redis (if needed)
kubectl cp $BACKUP_NAME/database/redis_dump.rdb <redis-pod>:/data/dump.rdb -n $NAMESPACE
kubectl exec -n $NAMESPACE <redis-pod> -- redis-cli DEBUG RESTART
\`\`\`

## Retention Policy
- Backups are retained for $RETENTION_DAYS days
- Automatic cleanup removes older backups

## Support
For restore assistance, contact: nikjois@llamasearch.ai
EOF

    log_success "Backup report generated: $BACKUP_DIR/BACKUP_REPORT_$TIMESTAMP.md"
}

# Main backup process
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}    OpenLogistics Backup Process       ${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    check_prerequisites
    echo ""
    
    backup_kubernetes_resources
    echo ""
    
    backup_database
    echo ""
    
    backup_persistent_volumes
    echo ""
    
    backup_application_data
    echo ""
    
    backup_monitoring_data
    echo ""
    
    create_backup_archive
    echo ""
    
    verify_backup
    echo ""
    
    cleanup_old_backups
    echo ""
    
    generate_backup_report
    echo ""
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}    BACKUP COMPLETED SUCCESSFULLY      ${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${GREEN}[COMPLETE] Backup created: $BACKUP_DIR/$BACKUP_NAME.tar.gz${NC}"
    echo -e "${BLUE}[INFO] Backup size: $(du -h "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)${NC}"
    echo -e "${BLUE}[INFO] See backup report for details${NC}"
}

# Handle script arguments
case "${1:-backup}" in
    "backup")
        main
        ;;
    "list")
        log_info "Available backups:"
        ls -lh "$BACKUP_DIR"/openlogistics_backup_*.tar.gz 2>/dev/null || log_warning "No backups found"
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    *)
        echo "Usage: $0 {backup|list|cleanup} [namespace]"
        exit 1
        ;;
esac
