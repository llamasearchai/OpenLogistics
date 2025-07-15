#!/bin/bash

# OpenLogistics Health Check Script
# Author: Nik Jois <nikjois@llamasearch.ai>
# Comprehensive health monitoring for OpenLogistics platform

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="${1:-open-logistics}"
TIMEOUT=30
HEALTH_ENDPOINT="/health"
API_ENDPOINT="/optimize"
METRICS_ENDPOINT="/metrics"

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

check_kubernetes_health() {
    log_info "Checking Kubernetes cluster health..."
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not available"
        return 1
    fi
    
    # Check cluster connectivity
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        return 1
    fi
    
    log_success "Kubernetes cluster is accessible"
    return 0
}

check_namespace() {
    log_info "Checking namespace: $NAMESPACE"
    
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_success "Namespace $NAMESPACE exists"
        return 0
    else
        log_error "Namespace $NAMESPACE does not exist"
        return 1
    fi
}

check_pods() {
    log_info "Checking pod health..."
    
    # Get pod status
    local pod_status=$(kubectl get pods -n "$NAMESPACE" -o json)
    local total_pods=$(echo "$pod_status" | jq '.items | length')
    local ready_pods=$(echo "$pod_status" | jq '[.items[] | select(.status.phase == "Running" and (.status.containerStatuses[]?.ready // false))] | length')
    
    if [ "$total_pods" -eq 0 ]; then
        log_error "No pods found in namespace $NAMESPACE"
        return 1
    fi
    
    if [ "$ready_pods" -eq "$total_pods" ]; then
        log_success "All $total_pods pods are ready"
        return 0
    else
        log_warning "$ready_pods/$total_pods pods are ready"
        
        # Show problematic pods
        kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running
        return 1
    fi
}

check_services() {
    log_info "Checking service health..."
    
    # Check if services exist
    local services=$(kubectl get services -n "$NAMESPACE" -o json)
    local service_count=$(echo "$services" | jq '.items | length')
    
    if [ "$service_count" -eq 0 ]; then
        log_error "No services found in namespace $NAMESPACE"
        return 1
    fi
    
    log_success "$service_count services are running"
    
    # Check service endpoints
    kubectl get endpoints -n "$NAMESPACE"
    return 0
}

check_deployments() {
    log_info "Checking deployment health..."
    
    local deployments=$(kubectl get deployments -n "$NAMESPACE" -o json)
    local deployment_count=$(echo "$deployments" | jq '.items | length')
    
    if [ "$deployment_count" -eq 0 ]; then
        log_error "No deployments found in namespace $NAMESPACE"
        return 1
    fi
    
    # Check each deployment
    local healthy_deployments=0
    for deployment in $(echo "$deployments" | jq -r '.items[].metadata.name'); do
        local ready_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')
        local desired_replicas=$(kubectl get deployment "$deployment" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
        
        if [ "$ready_replicas" = "$desired_replicas" ]; then
            log_success "Deployment $deployment: $ready_replicas/$desired_replicas replicas ready"
            ((healthy_deployments++))
        else
            log_warning "Deployment $deployment: $ready_replicas/$desired_replicas replicas ready"
        fi
    done
    
    if [ "$healthy_deployments" -eq "$deployment_count" ]; then
        return 0
    else
        return 1
    fi
}

check_api_health() {
    log_info "Checking API health..."
    
    # Get service endpoint
    local service_ip=$(kubectl get service open-logistics-service -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}' 2>/dev/null)
    
    if [ -z "$service_ip" ]; then
        log_error "Cannot find open-logistics-service"
        return 1
    fi
    
    # Port forward to test API
    kubectl port-forward service/open-logistics-service 8080:8000 -n "$NAMESPACE" &
    local port_forward_pid=$!
    
    # Wait for port forward to be ready
    sleep 3
    
    # Test health endpoint
    if curl -f -s "http://localhost:8080$HEALTH_ENDPOINT" > /dev/null 2>&1; then
        log_success "Health endpoint is responding"
        local health_status=0
    else
        log_error "Health endpoint is not responding"
        local health_status=1
    fi
    
    # Test API endpoint (if health is good)
    if [ "$health_status" -eq 0 ]; then
        if curl -f -s -X POST "http://localhost:8080$API_ENDPOINT" \
           -H "Content-Type: application/json" \
           -d '{"supply_chain_data":{"inventory":{"test":1}},"objectives":["minimize_cost"],"time_horizon":1}' > /dev/null 2>&1; then
            log_success "API endpoint is responding"
        else
            log_warning "API endpoint is not responding properly"
        fi
    fi
    
    # Cleanup port forward
    kill $port_forward_pid 2>/dev/null || true
    
    return $health_status
}

check_database_health() {
    log_info "Checking database health..."
    
    # Check PostgreSQL
    if kubectl get pod -l app=postgres -n "$NAMESPACE" &> /dev/null; then
        local postgres_ready=$(kubectl get pod -l app=postgres -n "$NAMESPACE" -o jsonpath='{.items[0].status.containerStatuses[0].ready}')
        if [ "$postgres_ready" = "true" ]; then
            log_success "PostgreSQL is ready"
        else
            log_error "PostgreSQL is not ready"
            return 1
        fi
    else
        log_warning "PostgreSQL not found (may not be deployed)"
    fi
    
    # Check Redis
    if kubectl get pod -l app=redis -n "$NAMESPACE" &> /dev/null; then
        local redis_ready=$(kubectl get pod -l app=redis -n "$NAMESPACE" -o jsonpath='{.items[0].status.containerStatuses[0].ready}')
        if [ "$redis_ready" = "true" ]; then
            log_success "Redis is ready"
        else
            log_error "Redis is not ready"
            return 1
        fi
    else
        log_warning "Redis not found (may not be deployed)"
    fi
    
    return 0
}

check_monitoring_health() {
    log_info "Checking monitoring stack health..."
    
    # Check Prometheus
    if kubectl get pod -l app=prometheus -n "$NAMESPACE" &> /dev/null; then
        local prometheus_ready=$(kubectl get pod -l app=prometheus -n "$NAMESPACE" -o jsonpath='{.items[0].status.containerStatuses[0].ready}')
        if [ "$prometheus_ready" = "true" ]; then
            log_success "Prometheus is ready"
        else
            log_error "Prometheus is not ready"
            return 1
        fi
    else
        log_warning "Prometheus not found"
    fi
    
    # Check Grafana
    if kubectl get pod -l app=grafana -n "$NAMESPACE" &> /dev/null; then
        local grafana_ready=$(kubectl get pod -l app=grafana -n "$NAMESPACE" -o jsonpath='{.items[0].status.containerStatuses[0].ready}')
        if [ "$grafana_ready" = "true" ]; then
            log_success "Grafana is ready"
        else
            log_error "Grafana is not ready"
            return 1
        fi
    else
        log_warning "Grafana not found"
    fi
    
    return 0
}

check_resource_usage() {
    log_info "Checking resource usage..."
    
    # CPU and Memory usage
    if kubectl top pods -n "$NAMESPACE" &> /dev/null; then
        log_success "Resource metrics available"
        kubectl top pods -n "$NAMESPACE"
    else
        log_warning "Resource metrics not available (metrics-server may not be installed)"
    fi
    
    # Storage usage
    kubectl get pvc -n "$NAMESPACE" 2>/dev/null || log_warning "No persistent volumes found"
    
    return 0
}

check_network_connectivity() {
    log_info "Checking network connectivity..."
    
    # Check service connectivity
    local services=$(kubectl get services -n "$NAMESPACE" -o json)
    local service_names=$(echo "$services" | jq -r '.items[].metadata.name')
    
    for service in $service_names; do
        local cluster_ip=$(kubectl get service "$service" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}')
        local port=$(kubectl get service "$service" -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].port}')
        
        if [ "$cluster_ip" != "None" ] && [ -n "$port" ]; then
            log_success "Service $service: $cluster_ip:$port"
        else
            log_warning "Service $service: No cluster IP or port"
        fi
    done
    
    return 0
}

generate_health_report() {
    log_info "Generating health report..."
    
    local timestamp=$(date)
    local report_file="HEALTH_REPORT_$(date +%Y%m%d_%H%M%S).md"
    
    cat > "$report_file" << EOF
# OpenLogistics Health Report

## Report Information
- **Timestamp**: $timestamp
- **Namespace**: $NAMESPACE
- **Generated By**: $(whoami)
- **Cluster**: $(kubectl config current-context)

## System Status

### Kubernetes Resources
\`\`\`
$(kubectl get all -n "$NAMESPACE")
\`\`\`

### Pod Details
\`\`\`
$(kubectl describe pods -n "$NAMESPACE")
\`\`\`

### Service Details
\`\`\`
$(kubectl describe services -n "$NAMESPACE")
\`\`\`

### Resource Usage
\`\`\`
$(kubectl top pods -n "$NAMESPACE" 2>/dev/null || echo "Metrics not available")
\`\`\`

### Recent Events
\`\`\`
$(kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -20)
\`\`\`

### Logs (Last 100 lines)
\`\`\`
$(kubectl logs -l app=open-logistics -n "$NAMESPACE" --tail=100 2>/dev/null || echo "No logs available")
\`\`\`

## Recommendations

1. Monitor resource usage regularly
2. Set up alerts for critical metrics
3. Review logs for any errors or warnings
4. Ensure backup strategies are in place
5. Test disaster recovery procedures

## Support
For issues, contact: nikjois@llamasearch.ai
EOF

    log_success "Health report generated: $report_file"
}

# Main health check process
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}    OpenLogistics Health Check         ${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    local overall_health=0
    
    # Run all health checks
    check_kubernetes_health || ((overall_health++))
    echo ""
    
    check_namespace || ((overall_health++))
    echo ""
    
    check_pods || ((overall_health++))
    echo ""
    
    check_services || ((overall_health++))
    echo ""
    
    check_deployments || ((overall_health++))
    echo ""
    
    check_api_health || ((overall_health++))
    echo ""
    
    check_database_health || ((overall_health++))
    echo ""
    
    check_monitoring_health || ((overall_health++))
    echo ""
    
    check_resource_usage || ((overall_health++))
    echo ""
    
    check_network_connectivity || ((overall_health++))
    echo ""
    
    generate_health_report
    echo ""
    
    # Overall health status
    if [ "$overall_health" -eq 0 ]; then
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}    SYSTEM HEALTH: EXCELLENT           ${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}[COMPLETE] All health checks passed!${NC}"
        exit 0
    elif [ "$overall_health" -le 2 ]; then
        echo -e "${YELLOW}========================================${NC}"
        echo -e "${YELLOW}    SYSTEM HEALTH: GOOD                ${NC}"
        echo -e "${YELLOW}========================================${NC}"
        echo -e "${YELLOW}[WARNING] Some minor issues detected${NC}"
        exit 1
    else
        echo -e "${RED}========================================${NC}"
        echo -e "${RED}    SYSTEM HEALTH: POOR                 ${NC}"
        echo -e "${RED}========================================${NC}"
        echo -e "${RED}[ERROR] Multiple issues detected${NC}"
        exit 2
    fi
}

# Execute main function
main "$@"
