# Changelog

## [1.3.1](https://github.com/canonical/authentik-server-operator/compare/v1.3.0...v1.3.1) (2026-09-04)


### Bug Fixes

* **deps:** update dependency lightkube-models to ~=1.37.0.8 ([8c9c2f1](https://github.com/canonical/authentik-server-operator/commit/8c9c2f1dcc37e3f39286eb80f8926451dc80a76d))
* **deps:** update dependency lightkube-models to ~=1.37.0.8 ([#101](https://github.com/canonical/authentik-server-operator/issues/101)) ([3ff2e27](https://github.com/canonical/authentik-server-operator/commit/3ff2e2746260b9a56b0688de739faeb0401e0f52))
* **deps:** update dependency ops-scenario to &lt;8.8.3 ([48ee661](https://github.com/canonical/authentik-server-operator/commit/48ee661cb913aa020b0d089dc7efcc194302cb08))
* **deps:** update dependency ops-scenario to &lt;8.8.3 ([#102](https://github.com/canonical/authentik-server-operator/issues/102)) ([c617547](https://github.com/canonical/authentik-server-operator/commit/c617547012a9b682a4395b6fdee2b45c1355e492))
* stop leaking Juju secret-backend tokens and erroring on lost Pebble ([dd42259](https://github.com/canonical/authentik-server-operator/commit/dd42259d80fa0a764858e7bdb86d9ed623fe2392))
* **terraform:** declare a minimum Juju provider version ([#92](https://github.com/canonical/authentik-server-operator/issues/92)) ([f397fd3](https://github.com/canonical/authentik-server-operator/commit/f397fd3f92e275d2873d1e29e5633c13b041ceaf))
* **terraform:** declare a minimum Juju provider version, not a pessimistic one ([abb8637](https://github.com/canonical/authentik-server-operator/commit/abb8637e2e32b201e08faac30436f89807e805e3))

## [1.3.0](https://github.com/canonical/authentik-server-operator/compare/v1.2.2...v1.3.0) (2026-08-19)


### Features

* add working COS metrics, alert rules and dashboard ([105a932](https://github.com/canonical/authentik-server-operator/commit/105a9326cb6193aede2da5304df1f72761b7e1ee))


### Bug Fixes

* converge the API token on a pre-existing database ([2c925e9](https://github.com/canonical/authentik-server-operator/commit/2c925e99ea313b0c713c3bd93920a933023efbd1))
* converge the API token on a pre-existing database ([#88](https://github.com/canonical/authentik-server-operator/issues/88)) ([0d216a1](https://github.com/canonical/authentik-server-operator/commit/0d216a1f8cfb34ce7f33f743f11674df1941dfa1))
* **deps:** update dependency lightkube to v1 ([f668db9](https://github.com/canonical/authentik-server-operator/commit/f668db973c230e07f74648460d5b73a1e3a648ee))
* **deps:** update dependency lightkube to v1 ([#85](https://github.com/canonical/authentik-server-operator/issues/85)) ([605962d](https://github.com/canonical/authentik-server-operator/commit/605962d90961b615df9e087346c2a464dfa26f5e))
* **deps:** update dependency lightkube-models to ~=1.36.3.8 ([1b92ecb](https://github.com/canonical/authentik-server-operator/commit/1b92ecb75f01406676e4836b546ef3ed54f350bf))
* **deps:** update dependency lightkube-models to ~=1.36.3.8 ([#78](https://github.com/canonical/authentik-server-operator/issues/78)) ([9495078](https://github.com/canonical/authentik-server-operator/commit/94950780200ce610c96192e8eecc51dc944e7986))
* **deps:** update dependency ops-scenario to &lt;8.8.2 ([3c5b3e8](https://github.com/canonical/authentik-server-operator/commit/3c5b3e8914ded8b3c4e003b9d356ae1325ce6a9d))
* **deps:** update dependency ops-scenario to &lt;8.8.2 ([#80](https://github.com/canonical/authentik-server-operator/issues/80)) ([853b7d8](https://github.com/canonical/authentik-server-operator/commit/853b7d869f1ae22592943730ef66ad3034af69b3))
* harden secret idempotency and Authentik API resilience ([ab785bc](https://github.com/canonical/authentik-server-operator/commit/ab785bc50e88443988c2478ef8a0f274cdd95743))
* support PostgreSQL read replicas and declare PgBouncer usage ([b654241](https://github.com/canonical/authentik-server-operator/commit/b654241207966f9e60c20b1a95874b363c658386))
* **terraform:** wire the worker Grafana dashboard and default to stable ([5e813f9](https://github.com/canonical/authentik-server-operator/commit/5e813f9f3aec263281769dfa2e6f641b7007d1d6))

## [1.2.2](https://github.com/canonical/authentik-server-operator/compare/v1.2.1...v1.2.2) (2026-07-24)


### Bug Fixes

* report the Authentik workload version, not Django's ([fe8fc57](https://github.com/canonical/authentik-server-operator/commit/fe8fc57b195b23d2e589c13ecfb57033d8ae1b6c))
* report the Authentik workload version, not Django's ([#71](https://github.com/canonical/authentik-server-operator/issues/71)) ([11b7975](https://github.com/canonical/authentik-server-operator/commit/11b79758566a1d0ba812d9a714aed977161aca9a))

## [1.2.1](https://github.com/canonical/authentik-server-operator/compare/v1.2.0...v1.2.1) (2026-07-24)


### Bug Fixes

* harden Authentik API interaction (resilience, caching) ([f8255f7](https://github.com/canonical/authentik-server-operator/commit/f8255f71deeeb70b63871624361ddc636c0927d0))

## [1.2.0](https://github.com/canonical/authentik-server-operator/compare/v1.1.0...v1.2.0) (2026-07-23)


### Features

* harden Authentik API integration and adopt api-token server-info contract ([1aac854](https://github.com/canonical/authentik-server-operator/commit/1aac8548118bbe438c74a95ead71c8b8b91ba4a3))


### Bug Fixes

* drop bootstrap-token fallback from server-info requirer (LIBPATCH 5) ([2ed3d43](https://github.com/canonical/authentik-server-operator/commit/2ed3d43c2650f3adb0617a4436230c3dfb865f0a))
* gate server-info publication on Authentik API readiness ([ecc4c8e](https://github.com/canonical/authentik-server-operator/commit/ecc4c8e2b40ab4b6064c6907de01ce8f3e8f2400))
* gate server-info publication on Authentik API readiness ([#66](https://github.com/canonical/authentik-server-operator/issues/66)) ([7975a92](https://github.com/canonical/authentik-server-operator/commit/7975a926563b2dcde44b40cd499de9cb4e7e8126))
* publish server-info promptly when the workload API recovers ([0d30d2f](https://github.com/canonical/authentik-server-operator/commit/0d30d2fc23c87e9d12ce3efd2345715e302511e0))
* publish server-info promptly when the workload API recovers ([#67](https://github.com/canonical/authentik-server-operator/issues/67)) ([923446e](https://github.com/canonical/authentik-server-operator/commit/923446e984cf4a4df77a2cd5fe2f6d6347858356))

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
