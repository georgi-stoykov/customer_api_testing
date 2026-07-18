# Code style

Formatting and linting are enforced by **Ruff** (`ruff format` + `ruff check`); config lives in
`pyproject.toml`. A **pre-commit** hook (`.pre-commit-config.yaml`) runs Ruff automatically on
`git commit`. After cloning, enable it once:

```
pip install -r requirements.txt
pre-commit install
```

To run the checks manually:

```
ruff check --fix engine tests
ruff format engine tests
```

## Rules

- **Imports** are **absolute** (`from engine.x import y`), never relative — enforced by Ruff
  `TID252` (`ban-relative-imports = "all"`). They keep the standard-library / third-party /
  first-party ordering but with **no blank lines between the groups** — one contiguous block
  (Ruff's isort `no-lines-before`).
- **Signatures with two or more parameters beyond `self`** are written one per line, ending with a
  magic trailing comma so Ruff keeps them exploded. Single-payload signatures (e.g.
  `get(self, uuid)`) stay on one line.
- **No magic string literals** for configuration or domain values. Give them a clearly named,
  single-source constant or enum:
  - config → `engine/constants/settings.py`
  - currencies → `engine/constants/currencies.py`
  - HTTP headers / media types / auth scheme → `engine/constants/http.py`
  - HTTP methods and status codes → stdlib `http.HTTPMethod` / `http.HTTPStatus`
  - endpoint paths → named constants in the resource module that uses them
  Test data values (amounts, references) are not config and may stay inline.
- **Every function is fully annotated** — all parameters and the return type, tests included
  (fixture-typed parameters, `-> None` returns) — enforced by Ruff's `ANN` rules
  (flake8-annotations). Bare `Any` is disallowed (`ANN401`): use the precise type, `object` for
  pass-through decorator `*args`/`**kwargs`, or a contained generic like `dict[str, Any]` where
  the payload is genuinely dynamic (transport JSON).
- **Enums use `StrEnum`** so a member equals its string value — safe in f-strings, comparisons, and
  JSON serialisation.
- **Money is `Decimal`**, never `float`.
- **Minimal comments.** Code should read on its own. The "why" lives in `.claude/CLAUDE.md`,
  `.docs/`, and this file — do not restate what the code already says.
