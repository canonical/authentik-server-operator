# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Constants for the Authentik server charm."""

from pathlib import Path

WORKLOAD_CONTAINER = "authentik"
WORKLOAD_SERVICE = "authentik-server"
COMMAND = "/lifecycle/ak server"
HTTP_PORT = 9000
HTTPS_PORT = 9443
HEALTH_CHECK_URL = f"http://localhost:{HTTP_PORT}/-/health/live/"
HEALTH_READY_URL = f"http://localhost:{HTTP_PORT}/-/health/ready/"

DATABASE_RELATION = "pg-database"
INGRESS_RELATION = "ingress"
CLUSTER_RELATION = "authentik-cluster"
SERVER_INFO_RELATION = "authentik-server-info"
PEER_RELATION = "authentik-peers"

LOGGING_RELATION_NAME = "logging"
PROMETHEUS_RELATION_NAME = "metrics-endpoint"
GRAFANA_RELATION_NAME = "grafana-dashboard"
TRACING_RELATION_NAME = "tracing"

SECRET_KEY_KEY = "secret-key"
BOOTSTRAP_TOKEN_KEY = "bootstrap-token"
BOOTSTRAP_PASSWORD_KEY = "bootstrap-password"

SECRETS_LABEL = "authentik-server-secrets"
SECRETS_PEER_KEY = "secrets_id"

PEBBLE_READY_CHECK_NAME = "ready"


CERTIFICATE_TRANSFER_INTEGRATION_NAME = "receive-ca-cert"

LOCAL_CERTIFICATES_PATH = Path("/tmp")
LOCAL_CERTIFICATES_FILE = LOCAL_CERTIFICATES_PATH / "ca-certificates.crt"
LOCAL_CHARM_CERTIFICATES_PATH = Path("/tmp/charm")
LOCAL_CHARM_CERTIFICATES_FILE = LOCAL_CHARM_CERTIFICATES_PATH / "charm-certificates.crt"
CERTIFICATES_PATH = Path("/etc/ssl/certs/")
CERTIFICATES_FILE = CERTIFICATES_PATH / "ca-certificates.crt"
