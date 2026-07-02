# Charmed Authentik Server

[![CharmHub Badge](https://charmhub.io/authentik-server/badge.svg)](https://charmhub.io/authentik-server)
[![Juju](https://img.shields.io/badge/Juju%20-3.0+-%23E95420)](https://github.com/juju/juju)
[![License](https://img.shields.io/github/license/canonical/authentik-server-operator?label=License)](https://github.com/canonical/authentik-server-operator/blob/main/LICENSE)

[![Continuous Integration Status](https://github.com/canonical/authentik-server-operator/actions/workflows/on_push.yaml/badge.svg?branch=main)](https://github.com/canonical/authentik-server-operator/actions?query=branch%3Amain)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196.svg)](https://conventionalcommits.org)

## Description

Charmed Authentik Server is an open-source, highly versatile Identity Provider focused on flexibility and integration. It provides unified authentication, user management, and authorization out-of-the-box, supporting industry-standard protocols such as OAuth2, OpenID Connect, SAML, and LDAP.

This operator manages the core Authentik Server application on Kubernetes, handling its deployment, configuration, scaling, and integration with required and optional dependencies in a declarative, automated manner using Juju.

## Usage & Deployment

### Basic Deployment

Authentik Server requires a PostgreSQL database to store its application state and a related Authentik Worker to handle background tasks (such as emails, task synchronization, and outposts).

To deploy a basic, fully functioning Authentik instance:

```shell
# Deploy the PostgreSQL database operator
juju deploy postgresql-k8s --channel 14/stable --trust

# Deploy the Authentik Server (this charm)
juju deploy authentik-server --trust

# Deploy the Authentik Worker operator
juju deploy authentik-worker --channel latest/edge --trust

# Integrate Authentik Server with the PostgreSQL database
juju integrate postgresql-k8s authentik-server

# Integrate Authentik Server with the Authentik Worker
juju integrate authentik-server:authentik-cluster authentik-worker:authentik-cluster
```

You can track the deployment status using:
```shell
watch -c juju status --color
```

Once the charms settle into an `active` and `idle` status, the Authentik Server is ready to use.

## Integrations

### PostgreSQL (`pg-database`)

An integration with [postgresql-k8s-operator](https://github.com/canonical/postgresql-k8s-operator) is **required**. The Authentik Server stores all configuration, users, and session data in this database.

### Authentik Worker (`authentik-cluster`)

An integration with [authentik-worker-operator](https://github.com/canonical/authentik-worker-operator) is **required**. The Authentik Worker handles background processes, outposts, and other asynchronous tasks for the cluster.

### Ingress (`ingress`)

An optional integration with [traefik-k8s-operator](https://github.com/canonical/traefik-k8s-operator) allows you to expose the Authentik web interface externally:

```shell
juju integrate traefik-k8s authentik-server:ingress
```

### Observability

Charmed Authentik Server offers seamless integration with the Canonical Observability Stack (COS) to forward logs, expose metrics, and export traces:

*   **Logging** (`logging`): Forward workload logs to Loki.
    ```shell
    juju integrate loki-k8s authentik-server:logging
    ```
*   **Metrics** (`metrics-endpoint`): Expose Prometheus scrape endpoints.
    ```shell
    juju integrate prometheus-k8s authentik-server:metrics-endpoint
    ```
*   **Dashboards** (`grafana-dashboard`): Import built-in Grafana monitoring dashboards.
    ```shell
    juju integrate grafana-k8s authentik-server:grafana-dashboard
    ```
*   **Tracing** (`tracing`): Send application trace data to Tempo.
    ```shell
    juju integrate tempo-k8s authentik-server:tracing
    ```

## Scenarios

### Retrieving Bootstrap Credentials

On the first start, Charmed Authentik Server automatically generates secure bootstrap credentials for the default administrator account, **`akadmin`**. These credentials are saved as a Juju secret.

To retrieve the generated password and token:

1. List the secrets in your model and find the ID associated with the `authentik-server-secrets` label:
   ```shell
   juju secrets --label authentik-server-secrets
   ```

2. Retrieve and reveal the secret contents using the secret URI (e.g., `secret:1234567890abc`):
   ```shell
   juju show-secret secret:<secret_id> --reveal
   ```

The revealed output will contain:
*   `bootstrap-password`: The password for the `akadmin` user.
*   `bootstrap-token`: The initial API bootstrap token.
*   `secret-key`: The encryption key used by the Authentik server.

## Security

Please see [SECURITY.md](https://github.com/canonical/authentik-server-operator/blob/main/SECURITY.md) for guidelines on reporting security issues.

## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines on enhancements to this charm following best practice guidelines, and [CONTRIBUTING.md](https://github.com/canonical/authentik-server-operator/blob/main/CONTRIBUTING.md) for developer guidance.

## License

The Charmed Authentik Server is free software, distributed under the Apache Software License, version 2.0. See [LICENSE](https://github.com/canonical/authentik-server-operator/blob/main/LICENSE) for more information.
