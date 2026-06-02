# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Constants for the Authentik server charm."""

WORKLOAD_CONTAINER = "authentik"
SERVICE_NAME = "authentik-server"
COMMAND = "ak server"
HTTP_PORT = 9000
HTTPS_PORT = 9443
HEALTH_CHECK_URL = "http://localhost:9000/-/health/live/"

DATABASE_RELATION = "pg-database"
INGRESS_RELATION = "ingress"
CLUSTER_RELATION = "authentik-cluster"
SERVER_INFO_RELATION = "authentik-server-info"
PEER_RELATION = "authentik-peers"

SECRET_KEY_PEER_KEY = "secret_key_secret_id"
BOOTSTRAP_TOKEN_PEER_KEY = "bootstrap_token_secret_id"
BOOTSTRAP_PASSWORD_PEER_KEY = "bootstrap_password_secret_id"
