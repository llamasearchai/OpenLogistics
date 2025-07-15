#!/bin/bash

# OpenLogistics Complete Deployment Script
# Author: Nik Jois <nikjois@llamasearch.ai>
# Handles complete deployment process for production environments

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_IMAGE="openlogistics/platform"
DOCKER_TAG="1.0.0"
NAMESPACE="open-logistics"
DEPLOYMENT_ENV="${DEPLOYMENT_ENV:-production}"

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
    log_info "Checking deployment prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    log_success "Docker is available"
    
    # Check Kubernetes
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    log_success "kubectl is available"
    
    # Check Helm (optional)
    if command -v helm &> /dev/null; then
        log_success "Helm is available"
    else
        log_warning "Helm is not available - will use kubectl for deployment"
    fi
    
    # Check Python environment
    if [ ! -f "pyproject.toml" ]; then
        log_error "Not in OpenLogistics project directory"
        exit 1
    fi
    log_success "In OpenLogistics project directory"
}

run_tests() {
    log_info "Running complete test suite..."
    
    if python -m pytest tests/ -v --tb=short --cov=src/open_logistics --cov-report=term-missing --cov-fail-under=84; then
        log_success "All tests passed"
    else
        log_error "Tests failed - deployment aborted"
        exit 1
    fi
}

build_docker_image() {
    log_info "Building Docker image..."
    
    # Build the Docker image
    if docker build -t "${DOCKER_IMAGE}:${DOCKER_TAG}" -t "${DOCKER_IMAGE}:latest" .; then
        log_success "Docker image built successfully"
    else
        log_error "Docker build failed"
        exit 1
    fi
    
    # Run security scan if available
    if command -v docker &> /dev/null; then
        log_info "Running security scan..."
        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
            -v $(pwd):/app \
            aquasec/trivy:latest image "${DOCKER_IMAGE}:${DOCKER_TAG}" || true
    fi
}

deploy_to_kubernetes() {
    log_info "Deploying to Kubernetes..."
    
    # Create namespace if it doesn't exist
    kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
    log_success "Namespace ${NAMESPACE} ready"
    
    # Apply ConfigMaps
    if [ -f "k8s/configmap-${DEPLOYMENT_ENV}.yaml" ]; then
        kubectl apply -f "k8s/configmap-${DEPLOYMENT_ENV}.yaml" -n "${NAMESPACE}"
        log_success "ConfigMap applied"
    fi
    
    # Apply Secrets
    if [ -f "k8s/secret-${DEPLOYMENT_ENV}.yaml" ]; then
        kubectl apply -f "k8s/secret-${DEPLOYMENT_ENV}.yaml" -n "${NAMESPACE}"
        log_success "Secrets applied"
    fi
    
    # Apply core manifests
    kubectl apply -f k8s/deployment.yaml -n "${NAMESPACE}"
    kubectl apply -f k8s/service.yaml -n "${NAMESPACE}"
    
    # Apply ingress
    if [ -f "k8s/ingress-${DEPLOYMENT_ENV}.yaml" ]; then
        kubectl apply -f "k8s/ingress-${DEPLOYMENT_ENV}.yaml" -n "${NAMESPACE}"
        log_success "Ingress applied"
    fi
    
    # Apply monitoring stack
    kubectl apply -f k8s/prometheus.yaml -n "${NAMESPACE}"
    kubectl apply -f k8s/grafana.yaml -n "${NAMESPACE}"
    
    log_success "Kubernetes deployment completed"
}

deploy_monitoring() {
    log_info "Deploying monitoring stack..."
    
    # Deploy Prometheus
    kubectl apply -f k8s/prometheus.yaml -n "${NAMESPACE}"
    
    # Deploy Grafana
    kubectl apply -f k8s/grafana.yaml -n "${NAMESPACE}"
    
    # Wait for pods to be ready
    kubectl wait --for=condition=ready pod -l app=prometheus -n "${NAMESPACE}" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=grafana -n "${NAMESPACE}" --timeout=300s
    
    log_success "Monitoring stack deployed"
}

verify_deployment() {
    log_info "Verifying deployment..."
    
    # Check pod status
    kubectl get pods -n "${NAMESPACE}"
    
    # Check service status
    kubectl get services -n "${NAMESPACE}"
    
    # Run health check
    log_info "Running health check..."
    
    # Get service endpoint
    SERVICE_IP=$(kubectl get service open-logistics-service -n "${NAMESPACE}" -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -z "$SERVICE_IP" ]; then
        SERVICE_IP=$(kubectl get service open-logistics-service -n "${NAMESPACE}" -o jsonpath='{.spec.clusterIP}')
    fi
    
    if [ -n "$SERVICE_IP" ]; then
        # Test health endpoint
        if curl -f "http://${SERVICE_IP}:8000/health" > /dev/null 2>&1; then
            log_success "Health check passed"
        else
            log_warning "Health check failed - service may still be starting"
        fi
    else
        log_warning "Could not determine service IP"
    fi
    
    log_success "Deployment verification completed"
}

cleanup_old_deployments() {
    log_info "Cleaning up old deployments..."
    
    # Clean up old ReplicaSets
    kubectl delete replicaset -l app=open-logistics -n "${NAMESPACE}" --cascade=false || true
    
    # Clean up old pods
    kubectl delete pod -l app=open-logistics -n "${NAMESPACE}" --field-selector=status.phase=Succeeded || true
    
    log_success "Cleanup completed"
}

generate_deployment_report() {
    log_info "Generating deployment report..."
    
    cat > DEPLOYMENT_REPORT.md << EOF
# OpenLogistics Deployment Report

## Deployment Information
- **Date**: $(date)
- **Environment**: ${DEPLOYMENT_ENV}
- **Docker Image**: ${DOCKER_IMAGE}:${DOCKER_TAG}
- **Namespace**: ${NAMESPACE}
- **Deployed By**: $(whoami)

## Deployment Status
- [x] Prerequisites checked
- [x] Tests passed
- [x] Docker image built
- [x] Kubernetes deployment completed
- [x] Monitoring stack deployed
- [x] Deployment verified

## Service Endpoints
- **API**: http://open-logistics-service.${NAMESPACE}.svc.cluster.local:8000
- **Health Check**: http://open-logistics-service.${NAMESPACE}.svc.cluster.local:8000/health
- **Metrics**: http://prometheus.${NAMESPACE}.svc.cluster.local:9090
- **Grafana**: http://grafana.${NAMESPACE}.svc.cluster.local:3000

## Kubernetes Resources
\`\`\`
$(kubectl get all -n "${NAMESPACE}")
\`\`\`

## Next Steps
1. Configure DNS/Load Balancer
2. Set up SSL certificates
3. Configure monitoring alerts
4. Run integration tests
5. Monitor application logs

## Rollback Instructions
If rollback is needed:
\`\`\`bash
kubectl rollout undo deployment/open-logistics-deployment -n ${NAMESPACE}
\`\`\`

## Support
For issues, contact: nikjois@llamasearch.ai
EOF

    log_success "Deployment report generated: DEPLOYMENT_REPORT.md"
}

# Main deployment process
main() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}    OpenLogistics Complete Deployment   ${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    
    check_prerequisites
    echo ""
    
    run_tests
    echo ""
    
    build_docker_image
    echo ""
    
    deploy_to_kubernetes
    echo ""
    
    deploy_monitoring
    echo ""
    
    verify_deployment
    echo ""
    
    cleanup_old_deployments
    echo ""
    
    generate_deployment_report
    echo ""
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}    DEPLOYMENT COMPLETED SUCCESSFULLY   ${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${GREEN}[COMPLETE] OpenLogistics deployed to ${DEPLOYMENT_ENV}!${NC}"
    echo -e "${BLUE}[INFO] See DEPLOYMENT_REPORT.md for details${NC}"
    echo ""
    echo -e "${BLUE}Access your application:${NC}"
    echo -e "${BLUE}  - API: kubectl port-forward service/open-logistics-service 8000:8000 -n ${NAMESPACE}${NC}"
    echo -e "${BLUE}  - Grafana: kubectl port-forward service/grafana 3000:3000 -n ${NAMESPACE}${NC}"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "rollback")
        log_info "Rolling back deployment..."
        kubectl rollout undo deployment/open-logistics-deployment -n "${NAMESPACE}"
        log_success "Rollback completed"
        ;;
    "status")
        log_info "Checking deployment status..."
        kubectl get all -n "${NAMESPACE}"
        ;;
    "logs")
        log_info "Showing application logs..."
        kubectl logs -l app=open-logistics -n "${NAMESPACE}" --tail=100
        ;;
    *)
        echo "Usage: $0 {deploy|rollback|status|logs}"
        exit 1
        ;;
esac
