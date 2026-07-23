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
TRAEFIK_ROUTE_RELATION = "traefik-route"
SMTP_RELATION = "smtp"
CLUSTER_RELATION = "authentik-cluster"
SERVER_INFO_RELATION = "authentik-server-info"
PEER_RELATION = "authentik-peers"

LOGGING_RELATION_NAME = "logging"
PROMETHEUS_RELATION_NAME = "metrics-endpoint"
GRAFANA_RELATION_NAME = "grafana-dashboard"
TRACING_RELATION_NAME = "tracing"
OAUTH_RELATION_NAME = "oauth"

SECRET_KEY_KEY = "secret-key"
BOOTSTRAP_TOKEN_KEY = "bootstrap-token"
BOOTSTRAP_PASSWORD_KEY = "bootstrap-password"

SECRETS_LABEL = "authentik-server-secrets"
SECRETS_PEER_KEY = "secrets_id"

OAUTH_SYNC_CACHE_PEER_KEY = "oauth_sync_cache"
OAUTH_MANAGED_NAMESPACE = "juju"
OAUTH_CACHE_SCHEMA_VERSION = 2
OAUTH_MODEL_UUID_HASH_LENGTH = 12
AUTHORIZATION_FLOW_CACHE_PEER_KEY = "authorization_flow_cache"
INVALIDATION_FLOW_CACHE_PEER_KEY = "invalidation_flow_cache"

PEBBLE_READY_CHECK_NAME = "ready"


CERTIFICATE_TRANSFER_INTEGRATION_NAME = "receive-ca-cert"

LOCAL_CERTIFICATES_PATH = Path("/tmp")
LOCAL_CERTIFICATES_FILE = LOCAL_CERTIFICATES_PATH / "ca-certificates.crt"
LOCAL_CHARM_CERTIFICATES_PATH = Path("/tmp/charm")
LOCAL_CHARM_CERTIFICATES_FILE = LOCAL_CHARM_CERTIFICATES_PATH / "charm-certificates.crt"
CERTIFICATES_PATH = Path("/etc/ssl/certs/")
CERTIFICATES_FILE = CERTIFICATES_PATH / "ca-certificates.crt"
