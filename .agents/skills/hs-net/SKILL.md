```markdown
# hs-net Development Patterns

> Auto-generated skill from repository analysis

## Overview

This skill teaches you the core development patterns, coding conventions, and workflows used in the `hs-net` Python codebase. You'll learn how to add features, update engine modules, maintain documentation, manage dependencies, and write tests in a way that aligns with the project's established practices. This guide is ideal for contributors seeking to make effective, consistent, and high-quality changes to the repository.

## Coding Conventions

- **File Naming:** Use `snake_case` for all Python files.
  - Example: `exceptions.py`, `shortcuts.py`, `aiohttp_engine.py`
- **Import Style:** Prefer relative imports within the package.
  - Example:
    ```python
    from .exceptions import CustomException
    from .engines import aiohttp_engine
    ```
- **Export Style:** Use named exports in `__init__.py` to expose public APIs.
  - Example (`src/hs_net/__init__.py`):
    ```python
    from .client import Client
    from .exceptions import CustomException

    __all__ = ["Client", "CustomException"]
    ```
- **Commit Messages:** Follow [Conventional Commits](https://www.conventionalcommits.org/) with prefixes like `feat`, `fix`, `docs`, `refactor`, `chore`.
  - Example: `feat: add async support to engine`

## Workflows

### Feature Addition with Tests
**Trigger:** When adding a new feature or API to the core library  
**Command:** `/add-feature`

1. Implement the feature in a new or existing module (e.g., `exceptions.py`, `shortcuts.py`).
2. Update `src/hs_net/__init__.py` to expose or register the new feature.
3. Add or update tests for the new feature in the appropriate test file.

**Example:**
```python
# src/hs_net/shortcuts.py
def quick_connect(url):
    # implementation

# src/hs_net/__init__.py
from .shortcuts import quick_connect
__all__.append("quick_connect")

# tests/test_shortcuts.py
def test_quick_connect():
    assert quick_connect("http://example.com")
```

---

### Engine Module Change with Tests
**Trigger:** When improving or refactoring engine modules (e.g., import strategies, dependency management)  
**Command:** `/update-engine`

1. Modify engine modules such as `aiohttp_engine.py`, `requests_engine.py`, etc.
2. Update `client.py` and/or `sync_client.py` to reflect engine changes.
3. Update or create tests related to engine behavior (e.g., `tests/test_engines.py`).

**Example:**
```python
# src/hs_net/engines/aiohttp_engine.py
def new_engine_feature():
    # implementation

# src/hs_net/client.py
from .engines.aiohttp_engine import new_engine_feature

# tests/test_engines.py
def test_new_engine_feature():
    assert new_engine_feature() is not None
```

---

### Documentation Update for Release or Feature
**Trigger:** When releasing a new version or adding significant features that require documentation updates  
**Command:** `/update-docs`

1. Update `README.md` with new features, installation, or usage instructions.
2. Update docs site files (`docs/docs/api/*.mdx`, `docs/docs/guide/*.mdx`, etc.) to document new APIs or guides.
3. Update or add example scripts in `examples/*.py` to demonstrate new features or changes.

**Example:**
```markdown
# README.md
## New: Quick Connect
Use `quick_connect(url)` for instant setup.

# docs/docs/api/shortcuts.mdx
export const meta = { title: "Shortcuts" }
## `quick_connect(url)`
...
```

---

### Dependency and Config Update
**Trigger:** When adding/removing dependencies, updating version numbers, or changing CI configuration  
**Command:** `/update-deps`

1. Modify `pyproject.toml` and/or `uv.lock` to update dependencies or version numbers.
2. Update `.github/workflows/*.yml` for CI/CD changes.
3. Update `src/hs_net/__init__.py` for version bump if needed.

**Example:**
```toml
# pyproject.toml
[tool.poetry.dependencies]
aiohttp = "^3.8.0"

# .github/workflows/ci.yml
- name: Run tests
  run: pytest

# src/hs_net/__init__.py
__version__ = "1.2.0"
```

## Testing Patterns

- **Test File Naming:** Test files are named using the pattern `test_*.py` and placed in the `tests/` directory.
- **Framework:** The specific test framework is not specified, but Python standards (e.g., `pytest`) are likely.
- **Test Structure:** Each feature or module typically has a corresponding test file.
  - Example:
    ```python
    # tests/test_exceptions.py
    def test_custom_exception():
        with pytest.raises(CustomException):
            raise CustomException("error")
    ```

## Commands

| Command        | Purpose                                               |
|----------------|------------------------------------------------------|
| /add-feature   | Add a new feature or API with corresponding tests    |
| /update-engine | Modify or refactor engine modules with tests         |
| /update-docs   | Update documentation and examples for new changes    |
| /update-deps   | Update dependencies, version numbers, or CI configs  |
```
