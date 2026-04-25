# Test Fixtures

Versioned fixture assets used by tests.

## Layout

- `docs/` document fixtures for parser/format/e2e scenarios
- `data/` json/yaml payload fixtures

## Current policy

- Large real-world `.docx` fixture remains in `samples/` for now:
  - `samples/南海鸢乌贼捕捞量智能反演文献综述_导出.docx`
- E2E tests resolve this fixture via path helper and environment overrides.
- New fixtures should be added under `tests/fixtures/docs/` first.

