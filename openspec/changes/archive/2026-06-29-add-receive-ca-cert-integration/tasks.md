## 1. Setup & Configuration

- [x] 1.1 Add the `receive-ca-cert` relation to the `requires` section of [charmcraft.yaml](file:///home/nikos.sklikas@canonical.com/.gemini/antigravity/worktrees/issue-6-receive-ca-cert/charmcraft.yaml).
- [x] 1.2 Run `charmcraft fetch-lib` to pull the `certificate_transfer` interface library into the project.
- [x] 1.3 Add certificate transfer constants and CA file paths to [src/constants.py](file:///home/nikos.sklikas@canonical.com/.gemini/antigravity/worktrees/issue-6-receive-ca-cert/src/constants.py).

## 2. Source Implementation

- [x] 2.1 Implement the `TLSCertificates` dataclass load logic in [src/integrations.py](file:///home/nikos.sklikas@canonical.com/.gemini/antigravity/worktrees/issue-6-receive-ca-cert/src/integrations.py).
- [x] 2.2 Implement `update_ca_certs` method on `WorkloadService` in [src/services.py](file:///home/nikos.sklikas@canonical.com/.gemini/antigravity/worktrees/issue-6-receive-ca-cert/src/services.py).
- [x] 2.3 Integrate, initialize, observe `receive-ca-cert` events and orchestrate `_ensure_tls()` in the holistic handler in [src/charm.py](file:///home/nikos.sklikas@canonical.com/.gemini/antigravity/worktrees/issue-6-receive-ca-cert/src/charm.py).

## 3. Testing & Verification

- [x] 3.1 Define CA certificate and subprocess mock fixtures in [tests/unit/conftest.py](file:///home/nikos.sklikas@canonical.com/.gemini/antigravity/worktrees/issue-6-receive-ca-cert/tests/unit/conftest.py).
- [x] 3.2 Add CA certificate update unit tests to [tests/unit/test_charm.py](file:///home/nikos.sklikas@canonical.com/.gemini/antigravity/worktrees/issue-6-receive-ca-cert/tests/unit/test_charm.py).
