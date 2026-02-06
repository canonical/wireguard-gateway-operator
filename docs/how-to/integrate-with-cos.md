(how_to_integrate_with_cos)=

# Integrate with COS

The WireGuard gateway charm provides metrics, logging, and Grafana dashboard integration with the COS solution. This integration is facilitated by the `cos-agent` relation interface with any charms compatible with the `cos-agent` relation interface, such as the [OpenTelemetry collector charm](https://charmhub.io/opentelemetry-collector).

## Integrate with OpenTelemetry collector charm

The OpenTelemetry collector charm is the entry point for all COS integrations. The OpenTelemetry collector charm installs the OpenTelemetry Collector on the WireGuard gateway charm machine and scrapes metrics, forwards logs, and transmits the Grafana dashboard to upstream metrics and logging charms like Prometheus and Loki, as well as to Grafana dashboard charms.

To integrate the OpenTelemetry collector charm with the WireGuard gateway charm, deploy the OpenTelemetry collector charm and integrate it with the `cos-agent` relation.

```
juju deploy opentelemetry-collector
juju integrate wireguard-gateway:cos-agent opentelemetry-collector
```

## Integrate with Prometheus charm

Once the WireGuard gateway charm is integrated with the OpenTelemetry collector charm, you can integrate the OpenTelemetry collector charm with the [Prometheus K8s](https://charmhub.io/prometheus-k8s) charm using the `send-remote-write` relation of the OpenTelemetry collector charm using a cross-model relation. This will instruct the OpenTelemetry collector charm to send all WireGuard gateway metrics to the remote Prometheus instance.

```
juju consume k8s:admin/cos.prometheus
juju integrate opentelemetry-collector:send-remote-write prometheus
```

<!-- vale Canonical.007-Headings-sentence-case = NO -->
## Integrate with Loki charm
<!-- vale Canonical.007-Headings-sentence-case = YES -->

You can integrate the OpenTelemetry collector charm with the [Loki K8s](https://charmhub.io/loki-k8s) charm using the `send-remote-write` relation of the OpenTelemetry collector charm using a cross-model relation. This will instruct the OpenTelemetry collector charm to send all logs on the machine to the remote Loki instance.

```
juju consume k8s:admin/cos.loki
juju integrate opentelemetry-collector:send-loki-logs loki
```

## Integrate with Grafana charm

You can integrate the OpenTelemetry collector charm with the [Grafana K8s](https://charmhub.io/grafana-k8s) charm using the `grafana-dashboards-provider` relation of the OpenTelemetry collector charm using a cross-model relation. This will instruct the OpenTelemetry collector charm to relay the WireGuard gateway Grafana dashboard to the remote Grafana instance.

```
juju consume k8s:admin/cos.grafana
juju integrate opentelemetry-collector:grafana-dashboards-provider grafana
```
