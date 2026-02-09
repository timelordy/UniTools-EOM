# CI/CD Pipeline Documentation

## Обзор

EOMTemplateTools использует GitHub Actions для автоматизации тестирования, линтинга и релизов.

## Workflows

### 1. **CI (Continuous Integration)** - `.github/workflows/ci.yml`

**Триггеры:**
- Push в `main` или `develop`
- Pull Request в `main` или `develop`

**Jobs:**

#### Test & Lint
1. **Code Formatting Check** (black)
   - Проверяет соответствие black style guide
   - Останавливает CI при несоответствии

2. **Import Sorting Check** (isort)
   - Проверяет сортировку импортов
   - Совместим с black (profile="black")

3. **Linting** (flake8)
   - Фатальные ошибки: `E9,F63,F7,F82` (syntax, undefined names)
   - Warnings: все остальные (не останавливают CI)
   - Max complexity: 10
   - Line length: 120

4. **Type Checking** (mypy)
   - Проверка типов в lib/
   - `continue-on-error: true` - не блокирует CI (incremental migration)

5. **Tests** (pytest)
   - Запуск всех тестов в `tests/`
   - Coverage report (term, HTML, XML)
   - Upload to Codecov (если настроен CODECOV_TOKEN)

6. **Coverage Threshold**
   - Минимум: **60%** coverage
   - Fail CI если ниже порога
   - Постепенно увеличивать до 80%

#### Security Scan
- **Bandit** - поиск security issues
- `continue-on-error: true` - не блокирует CI

---

### 2. **Release** - `.github/workflows/release.yml`

**Триггеры:**
- Push тега вида `v*.*.*` (например, `v0.2.0`, `v0.3.1`)

**Процесс:**
1. Checkout кода
2. Извлечение версии из тега (`v0.2.0` → `0.2.0`)
3. Извлечение changelog для версии из `CHANGELOG.md`
4. Создание ZIP архива extension
5. Создание GitHub Release с:
   - Описанием из CHANGELOG
   - Прикреплённым ZIP файлом
   - Draft: false (сразу публикуется)
   - Prerelease: auto-detect (`alpha`, `beta`, `rc`)

**Как сделать релиз:**
```bash
# 1. Обновить версию в pyproject.toml
version = "0.3.0"

# 2. Обновить CHANGELOG.md
## [0.3.0] - 2026-02-10
### Added
- New feature X

# 3. Commit
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 0.3.0"

# 4. Create tag
git tag v0.3.0

# 5. Push tag (triggers release)
git push origin v0.3.0
```

---

### 3. **Code Quality** - `.github/workflows/code-quality.yml`

**Триггеры:**
- Расписание: каждый понедельник в 8:00 UTC
- Manual trigger (workflow_dispatch)

**Генерирует:**
1. **Cyclomatic Complexity** (radon cc)
2. **Maintainability Index** (radon mi)
3. **TODO/FIXME Count**
4. **Lines of Code**
5. **Test Coverage Summary**

**Output:** Artifact `code-quality-report.md` (30 дней)

---

### 4. **Tests** (extended) - `.github/workflows/tests.yml`

**Дополнительный workflow для matrix testing:**

- Python versions: 3.8, 3.9, 3.10, 3.11
- Parallel execution
- Coverage upload to Codecov
- Coverage comment на Pull Requests

**Используется для:**
- Проверки совместимости с разными Python версиями
- Детальный coverage report

---

## Secrets Configuration

### GitHub Secrets (Settings → Secrets and Variables → Actions)

| Secret | Описание | Обязательный |
|--------|----------|--------------|
| `CODECOV_TOKEN` | Token для Codecov.io | Нет (optional) |
| `GITHUB_TOKEN` | Auto-generated | Да (auto) |

### Codecov Setup (Optional)

1. Зарегистрироваться на [codecov.io](https://codecov.io/)
2. Добавить репозиторий
3. Скопировать token
4. Добавить в GitHub Secrets как `CODECOV_TOKEN`

---

## Status Badges

Добавить в README.md:

```markdown
[![CI](https://github.com/your-username/EOMTemplateTools/workflows/CI/badge.svg)](https://github.com/your-username/EOMTemplateTools/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/your-username/EOMTemplateTools/branch/main/graph/badge.svg)](https://codecov.io/gh/your-username/EOMTemplateTools)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
```

---

## Локальная проверка (перед push)

```bash
# 1. Formatting
black EOMTemplateTools.extension/lib tests
isort EOMTemplateTools.extension/lib tests

# 2. Linting
flake8 EOMTemplateTools.extension/lib tests --max-line-length=120

# 3. Type checking
mypy EOMTemplateTools.extension/lib

# 4. Tests
pytest tests/ -v --cov

# Или всё сразу через pre-commit:
pre-commit run --all-files
```

---

## Pre-commit Hooks

Уже настроены в `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=120]
```

**Установка:**
```bash
pip install pre-commit
pre-commit install
```

Теперь проверки запускаются автоматически при `git commit`.

---

## Troubleshooting

### CI fails на black check

```bash
# Автофикс локально:
black EOMTemplateTools.extension/lib tests

# Коммит:
git add -u
git commit -m "style: apply black formatting"
```

### CI fails на coverage threshold

```bash
# Запустить тесты локально:
pytest tests/ --cov --cov-report=html

# Открыть htmlcov/index.html
# Найти непокрытые модули, добавить тесты
```

### Release не создаётся

**Проверить:**
1. Тег создан правильно: `v0.2.0` (не `0.2.0`)
2. Тег запушен: `git push origin v0.2.0`
3. CHANGELOG.md содержит секцию `## [0.2.0]`

---

## Roadmap

### Планируется добавить:

- [ ] **Dependabot** - автообновление dependencies
- [ ] **CodeQL** - advanced security scanning
- [ ] **Sphinx docs** - автогенерация API docs
- [ ] **Performance benchmarks** - tracking performance regressions
- [ ] **Docker image** - для консистентного тестирования

---

**Последнее обновление:** 2026-02-09
