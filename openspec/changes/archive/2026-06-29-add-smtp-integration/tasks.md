## 1. Setup and Metadata Configuration

- [x] 1.1 Add `smtp` relation configuration to `charmcraft.yaml`
- [x] 1.2 Add `SMTP_RELATION = "smtp"` to `src/constants.py`

## 2. Integration Logic and Data Parsing

- [x] 2.1 Implement `SmtpData` dataclass in `src/integrations.py` to parse SMTP relation data and generate double-underscore Authentik mail config env vars
- [x] 2.2 Initialize `SmtpRequires` and hook up its observer in `src/charm.py`
- [x] 2.3 Merge the loaded `SmtpData` into the `_pebble_layer` property in `src/charm.py`

## 3. Verification and Unit Testing

- [x] 3.1 Create/update unit tests in `tests/unit/test_charm.py` to verify that SMTP integration data is parsed and applied properly to the Pebble service environment
