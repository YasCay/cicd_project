# Reddit Sentiment Pipeline Helm Chart

This Helm chart deploys the Reddit sentiment analysis pipeline as a Kubernetes CronJob that runs every 3 hours.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- Reddit API credentials
- Persistent storage (optional but recommended)

## Installation

To install the chart with the release name `reddit-sentiment`:

```bash
helm install reddit-sentiment ./reddit-sentiment-pipeline \
  --set reddit.clientId="your_reddit_client_id" \
  --set reddit.clientSecret="your_reddit_client_secret"
```

To upgrade an existing release:

```bash
helm upgrade reddit-sentiment ./reddit-sentiment-pipeline
```

To uninstall the release:

```bash
helm uninstall reddit-sentiment
```

## Installing the Chart

To install the chart with the release name `reddit-sentiment`:

```bash
helm install reddit-sentiment ./reddit-sentiment-pipeline \
  --set reddit.clientId="your_reddit_client_id" \
  --set reddit.clientSecret="your_reddit_client_secret"
```

## Configuration

The following table lists the configurable parameters of the chart and their default values.

## Values

The following table lists the configurable parameters and their default values:

### Global Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `global.imageRegistry` | Global Docker image registry | `ghcr.io` |
| `global.imagePullSecrets` | Global Docker registry secret names | `[]` |

### Application Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `app.name` | Application name | `reddit-sentiment-pipeline` |
| `app.version` | Application version | `1.0.0` |

### Image Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `image.repository` | Image repository | `your-username/reddit-sentiment-pipeline` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `image.tag` | Image tag | `latest` |

### CronJob Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `cronjob.schedule` | Cron schedule expression | `0 */3 * * *` (every 3 hours) |
| `cronjob.timezone` | Timezone for the schedule | `UTC` |
| `cronjob.concurrencyPolicy` | How to handle concurrent executions | `Forbid` |
| `cronjob.successfulJobsHistoryLimit` | Number of successful jobs to keep | `3` |
| `cronjob.failedJobsHistoryLimit` | Number of failed jobs to keep | `1` |
| `cronjob.restartPolicy` | Pod restart policy | `OnFailure` |
| `cronjob.backoffLimit` | Number of retries before marking job as failed | `3` |
| `cronjob.activeDeadlineSeconds` | Job timeout in seconds | `3600` (1 hour) |

### Reddit API Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `reddit.clientId` | Reddit API client ID | `""` |
| `reddit.clientSecret` | Reddit API client secret | `""` |
| `reddit.userAgent` | Reddit API user agent | `reddit-sentiment-pipeline/1.0` |
| `reddit.subreddits` | Comma-separated list of subreddits | `CryptoCurrency,Bitcoin,ethereum` |

### Resource Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `job.resources.requests.memory` | Memory request | `512Mi` |
| `job.resources.requests.cpu` | CPU request | `250m` |
| `job.resources.limits.memory` | Memory limit | `2Gi` |
| `job.resources.limits.cpu` | CPU limit | `1000m` |

### Persistence Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `persistence.enabled` | Enable persistent storage | `true` |
| `persistence.storageClass` | Storage class | `""` |
| `persistence.accessMode` | Access mode | `ReadWriteOnce` |
| `persistence.size` | Storage size | `10Gi` |
| `persistence.mountPath` | Mount path for data | `/app/data` |

### Monitoring Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `metrics.enabled` | Enable metrics collection | `true` |
| `metrics.port` | Metrics server port | `8000` |
| `metrics.serviceMonitor.enabled` | Enable ServiceMonitor for Prometheus | `false` |
| `monitoring.alerts.enabled` | Enable alerting rules | `true` |

## Examples

### Basic Installation

```bash
helm install reddit-sentiment ./reddit-sentiment-pipeline \
  --set reddit.clientId="your_client_id" \
  --set reddit.clientSecret="your_client_secret"
```

### Production Installation with Monitoring

```bash
helm install reddit-sentiment ./reddit-sentiment-pipeline \
  --set reddit.clientId="your_client_id" \
  --set reddit.clientSecret="your_client_secret" \
  --set persistence.enabled=true \
  --set persistence.size=50Gi \
  --set metrics.serviceMonitor.enabled=true \
  --set monitoring.alerts.enabled=true \
  --set job.resources.limits.memory=4Gi \
  --set job.resources.limits.cpu=2000m
```

### Custom Schedule

```bash
# Run every hour instead of every 3 hours
helm install reddit-sentiment ./reddit-sentiment-pipeline \
  --set reddit.clientId="your_client_id" \
  --set reddit.clientSecret="your_client_secret" \
  --set cronjob.schedule="0 * * * *"
```

## Upgrading

```bash
helm upgrade reddit-sentiment ./reddit-sentiment-pipeline \
  --set reddit.clientId="your_client_id" \
  --set reddit.clientSecret="your_client_secret"
```

## Uninstalling

```bash
helm uninstall reddit-sentiment
```

## Monitoring

When monitoring is enabled, the chart provides:

- Prometheus metrics on port 8000
- ServiceMonitor for automatic Prometheus discovery
- AlertManager rules for job failures and performance issues
- Grafana dashboard (see `dashboards/` directory)

## Security

The chart implements several security best practices:

- Non-root user execution
- Read-only root filesystem
- Dropped capabilities
- Network policies (optional)
- Secret management for sensitive data

## Troubleshooting

### Check CronJob Status

```bash
kubectl get cronjobs
kubectl describe cronjob reddit-sentiment-reddit-sentiment-pipeline
```

### Check Job Logs

```bash
kubectl get jobs -l app.kubernetes.io/instance=reddit-sentiment
kubectl logs -l app.kubernetes.io/instance=reddit-sentiment
```

### Check Persistent Volume

```bash
kubectl get pvc
kubectl describe pvc reddit-sentiment-reddit-sentiment-pipeline-data
```
