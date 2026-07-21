# Changelog

## [1.1.0](https://github.com/canonical/authentik-server-operator/compare/v1.0.0...v1.1.0) (2026-07-21)


### Features

* **terraform:** add oauth juju offer ([#55](https://github.com/canonical/authentik-server-operator/issues/55)) ([9657310](https://github.com/canonical/authentik-server-operator/commit/9657310504d399714521f1d70140c37f205f4721))
* **terraform:** integrate LDAP outpost with traefik-route cross-model offer ([ca8edd8](https://github.com/canonical/authentik-server-operator/commit/ca8edd8ab139917d216f422918f4110e6750aae5))
* **terraform:** integrate LDAP outpost with traefik-route cross-model offer ([#58](https://github.com/canonical/authentik-server-operator/issues/58)) ([29992d6](https://github.com/canonical/authentik-server-operator/commit/29992d69471e5db33d12d9b31d83b278e1f26fa9))


### Bug Fixes

* add oauth juju offer ([1c83cc6](https://github.com/canonical/authentik-server-operator/commit/1c83cc620062682f37cb447de791d96f6857afac))

## 1.0.0 (2026-07-17)


### Features

* add observability charm libraries ([4968cbc](https://github.com/canonical/authentik-server-operator/commit/4968cbcb238e7564c052c2fec4802cff45f58c69))
* **config:** add PostgreSQL pooling and expose recovery/source routes ([aa154ce](https://github.com/canonical/authentik-server-operator/commit/aa154ceb7a9ee8152bf3e87e8d5be6cc22e37d33))
* **config:** add PostgreSQL pooling and expose recovery/source routes ([#50](https://github.com/canonical/authentik-server-operator/issues/50)) ([5f3b442](https://github.com/canonical/authentik-server-operator/commit/5f3b442b24631e306a802813d47276e0216b5e35))
* implement admin credentials retrieval and recovery link actions ([a5584cc](https://github.com/canonical/authentik-server-operator/commit/a5584cc8d3af38e6532428dd63eb9b148d75ea6a))
* implement admin credentials retrieval and recovery link actions ([#53](https://github.com/canonical/authentik-server-operator/issues/53)) ([317c119](https://github.com/canonical/authentik-server-operator/commit/317c11926463a7e5f79507ade933b9d2bc982353))
* implement charm core functionality ([efdc69d](https://github.com/canonical/authentik-server-operator/commit/efdc69dc3f0a9030a86969fe281cd5386c81fd8f))
* implement charm core functionality ([9a95dd7](https://github.com/canonical/authentik-server-operator/commit/9a95dd7a2ec367b6eef57a09b3e23efc3d148607))
* integrate secure traefik-route relation and remove legacy ingress ([a181a60](https://github.com/canonical/authentik-server-operator/commit/a181a60d166e274037b2cf919ca793a6847136e2))
* support arm64 ([782a7d1](https://github.com/canonical/authentik-server-operator/commit/782a7d1d3bdac9f8f68baefd7245757ceb16462b))
* support arm64 ([#29](https://github.com/canonical/authentik-server-operator/issues/29)) ([4447c7a](https://github.com/canonical/authentik-server-operator/commit/4447c7a4fb4cb61476bdc50bdd461c2f47d0eafe))
* **terraform:** use traefik-route instead of legacy ingress in requires output ([726f387](https://github.com/canonical/authentik-server-operator/commit/726f387b4e26f6c1ebe7430e6acc9c7bb1b7140e))
* update authentik charm libraries ([2448e92](https://github.com/canonical/authentik-server-operator/commit/2448e92a10d097bb09255c6b1049b672ac2917a8))
* update authentik_cluster and authentik_server_info library APIs ([0cd7590](https://github.com/canonical/authentik-server-operator/commit/0cd75902e5698ef79d14d1719a07a988d44085cd))


### Bug Fixes

* add oauth relation ([6bc9442](https://github.com/canonical/authentik-server-operator/commit/6bc9442506b036cbacb0025753f62cf0151db5db))
* add recieve-ca-cert relation ([48ba486](https://github.com/canonical/authentik-server-operator/commit/48ba486c7639f8cf5abec23e8e692bd49eee4114))
* add smtp integration ([de06439](https://github.com/canonical/authentik-server-operator/commit/de064391fb524a7e2b106e3c11b277a45b8edf28))
* correctly parse application status on startup ([6a47701](https://github.com/canonical/authentik-server-operator/commit/6a47701c1609ad25dea448e8870a959caa51dcb2))
* **deps:** update dependency cosl to ~=1.10.1 ([294787d](https://github.com/canonical/authentik-server-operator/commit/294787d50960b3ec6f6d21aabcf230811cda1520))
* **deps:** update dependency cosl to ~=1.10.1 ([#40](https://github.com/canonical/authentik-server-operator/issues/40)) ([50de962](https://github.com/canonical/authentik-server-operator/commit/50de962e5c6aa0aa0baea5f0df5687783b0cdbf6))
* **deps:** update dependency cosl to ~=1.9.2 ([8adfc9d](https://github.com/canonical/authentik-server-operator/commit/8adfc9deebf9ff8d55b23ee3f6becdd6cb268d78))
* **deps:** update dependency cosl to ~=1.9.2 ([#21](https://github.com/canonical/authentik-server-operator/issues/21)) ([07bdcb9](https://github.com/canonical/authentik-server-operator/commit/07bdcb9e8fdbd78e84d92787dd937bc09c5a6bcc))
* **deps:** update dependency lightkube to ~=0.22.0 ([e5ae42a](https://github.com/canonical/authentik-server-operator/commit/e5ae42af17d8ee296a1a64bf33a817d3f4372416))
* **deps:** update dependency lightkube to ~=0.22.0 ([#35](https://github.com/canonical/authentik-server-operator/issues/35)) ([d07f269](https://github.com/canonical/authentik-server-operator/commit/d07f2696e7942d28151451dea9c3fe7e329ed4a6))
* **deps:** update dependency ops-scenario to &lt;8.8.1 ([51b7056](https://github.com/canonical/authentik-server-operator/commit/51b7056bb000e68ef0f79909108adfb0dcb15c09))
* **deps:** update dependency ops-scenario to &lt;8.8.1 ([#27](https://github.com/canonical/authentik-server-operator/issues/27)) ([11603cc](https://github.com/canonical/authentik-server-operator/commit/11603cc2b9ba68675cd5caaf3ffac88c24aa0952))
* handle missing secret ([75a030a](https://github.com/canonical/authentik-server-operator/commit/75a030a3ebc6208a624514aefc4354eddd560979))
* **oauth:** resolve OIDC provider schema and routing compatibility with Authentik 2026.5 ([86b902c](https://github.com/canonical/authentik-server-operator/commit/86b902c5da575d96608a2b3b4a6bd8fa001710a5))
* route  to authentik ([2b4c516](https://github.com/canonical/authentik-server-operator/commit/2b4c5164e7f92c5667a485fa294c59d7bfce5b93))
* set env vars ([773cbb6](https://github.com/canonical/authentik-server-operator/commit/773cbb6ca0c9c7ee48aa5f39a4fb5a9df349c99b))
* unit tests ([2343fdc](https://github.com/canonical/authentik-server-operator/commit/2343fdc409236a71ac9c0faf957058e1a40e7c8e))
