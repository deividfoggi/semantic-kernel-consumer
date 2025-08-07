# Kubernetes Deployment for Semantic Kernel Consumer

This directory contains Kubernetes manifests for deploying the semantic-kernel-consumer application to Azure Kubernetes Service (AKS).

## Files Overview

- `deployment.yaml` - Main deployment manifest with all required resources
- `workload-identity.yaml` - Azure Workload Identity configuration (optional)

## Prerequisites

1. **AKS Cluster** with the following features enabled:
   - Azure Workload Identity (recommended)
   - Azure Container Registry integration

2. **Azure Resources**:
   - Azure Container Registry (genaigateway.azurecr.io)
   - Azure Service Bus
   - Azure Storage Account
   - Azure OpenAI Service
   - Azure Managed Identity (if using Workload Identity)

## Deployment Steps

### 1. Configure Secrets and ConfigMaps

Before deploying, update the following in `deployment.yaml`:

**ConfigMap (`azure-config`):**
```yaml
data:
  openai-endpoint: "https://your-actual-openai-resource.openai.azure.com/"
  client-id: "your-actual-managed-identity-client-id"
```

**Secret (`azure-secrets`):**
Replace the base64 encoded placeholder values with your actual secrets:

```bash
# Encode your actual connection strings
echo -n "your-actual-service-bus-connection-string" | base64
echo -n "your-actual-storage-connection-string" | base64
echo -n "your-actual-openai-api-key" | base64
```

### 2. Deploy to AKS

```bash
# Apply the deployment
kubectl apply -f deployment.yaml

# Check deployment status
kubectl get pods -n semantic-kernel-consumer
kubectl get services -n semantic-kernel-consumer

# View logs
kubectl logs -f deployment/semantic-kernel-consumer -n semantic-kernel-consumer
```

### 3. Optional: Configure Azure Workload Identity

For enhanced security, configure Azure Workload Identity instead of using connection strings:

1. Create a Managed Identity in Azure
2. Assign appropriate permissions to Azure resources
3. Configure the federated credential
4. Update `workload-identity.yaml` with your values
5. Apply the workload identity configuration:

```bash
kubectl apply -f workload-identity.yaml
```

## Configuration Details

### Resource Limits
- **Memory**: 256Mi request, 512Mi limit
- **CPU**: 100m request, 500m limit

### Security Features
- Runs as non-root user (UID 1000)
- Read-only root filesystem
- Network policies for traffic control
- Pod disruption budget for availability

### Health Checks
- **Liveness Probe**: Checks if the application is running
- **Readiness Probe**: Checks if the application is ready to serve traffic

### Scaling
- Default: 2 replicas
- Rolling update strategy
- Pod disruption budget ensures at least 1 pod is available during updates

## Monitoring and Troubleshooting

```bash
# Check pod status
kubectl get pods -n semantic-kernel-consumer

# View pod logs
kubectl logs -f <pod-name> -n semantic-kernel-consumer

# Describe pod for events
kubectl describe pod <pod-name> -n semantic-kernel-consumer

# Check service endpoints
kubectl get endpoints -n semantic-kernel-consumer

# Test connectivity
kubectl exec -it <pod-name> -n semantic-kernel-consumer -- /bin/sh
```

## Environment Variables

The deployment configures the following environment variables:

- `PYTHONUNBUFFERED=1`
- `PYTHONDONTWRITEBYTECODE=1`
- `SHUTDOWN_TIMEOUT=30`
- `AZURE_SERVICE_BUS_CONNECTION_STRING` (from secret)
- `AZURE_STORAGE_CONNECTION_STRING` (from secret)
- `AZURE_OPENAI_ENDPOINT` (from configmap)
- `AZURE_OPENAI_API_KEY` (from secret)
- `AZURE_CLIENT_ID` (from configmap, for Workload Identity)

## Network Policy

A NetworkPolicy is included that:
- Allows ingress from ingress-nginx namespace on port 8080
- Allows egress to HTTPS (443) and DNS (53) for Azure service communication

## Updates and Rollbacks

```bash
# Update the image
kubectl set image deployment/semantic-kernel-consumer semantic-kernel-consumer=genaigateway.azurecr.io/semantic-kernel-consumer:0.2 -n semantic-kernel-consumer

# Check rollout status
kubectl rollout status deployment/semantic-kernel-consumer -n semantic-kernel-consumer

# Rollback if needed
kubectl rollout undo deployment/semantic-kernel-consumer -n semantic-kernel-consumer
```
