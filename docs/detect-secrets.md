# Detect-Secrets: Краткий гайд

## Установка

```bash
# Базовая установка
pip install detect-secrets

# С дополнительными возможностями
pip install detect-secrets[word_list,gibberish]

# Для Python проектов с uv
uv add --group dev detect-secrets
```

## Быстрый старт

### 1. Создание baseline
```bash
# Создать baseline для текущего проекта
detect-secrets scan > .secrets.baseline

# Исключить определенные файлы
detect-secrets scan --exclude-files 'uv\.lock$' --exclude-files '__pycache__/.*' > .secrets.baseline

# Сканировать все файлы (не только git-tracked)
detect-secrets scan --all-files > .secrets.baseline
```

### 2. Обновление baseline
```bash
# Добавить новые секреты в существующий baseline
detect-secrets scan --baseline .secrets.baseline
```

### 3. Аудит найденных секретов
```bash
# Интерактивный аудит - пометить секреты как true/false positive
detect-secrets audit .secrets.baseline

# Статистика после аудита
detect-secrets audit --stats .secrets.baseline

# Отчет в JSON
detect-secrets audit --report .secrets.baseline
```

### 4. Что делать после ошибки в pre-commit

Когда `detect-secrets` находит секрет в pre-commit hook, выполни эти шаги:

```bash
# ШАГ 1: Посмотри что именно найдено
echo "Найденный секрет:"
git status --porcelain | grep "^[AM]" | cut -c4- | xargs grep -n "секретная_строка"

# ШАГ 2: Запусти интерактивный аудит
uv run detect-secrets audit .secrets.baseline

# ШАГ 3: После аудита обнови baseline
uv run detect-secrets scan --baseline .secrets.baseline

# ШАГ 4: Попробуй commit снова
git commit -m "твое сообщение"
```

**Быстрый способ для ложных срабатываний:**
```bash
# Добавь inline комментарий прямо в файл
# pragma: allowlist secret

# Или на следующей строке
# pragma: allowlist nextline secret
```

**Интерактивный аудит - что нажимать:**
- `y` - это настоящий секрет (исправь код)
- `n` - ложное срабатывание (безопасно)
- `s` - пропустить (оставить без изменений)
- `q` - выйти из аудита

## Pre-commit hook

### .pre-commit-config.yaml
```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
        exclude: uv\.lock$
```

### Проверка изменений вручную
```bash
# Проверить только staged файлы
git diff --staged --name-only -z | xargs -0 detect-secrets-hook --baseline .secrets.baseline

# Проверить все tracked файлы
git ls-files -z | xargs -0 detect-secrets-hook --baseline .secrets.baseline
```

## Исключения

### Файлы
```bash
# Исключить файлы по regex
detect-secrets scan --exclude-files '.*\.lock$' --exclude-files '__pycache__/.*'
```

### Строки
```bash
# Исключить строки по regex
detect-secrets scan --exclude-lines 'password = (test|fake)'
```

### Секреты
```bash
# Исключить конкретные значения
detect-secrets scan --exclude-secrets 'fakesecret' --exclude-secrets '\${.*}'
```

## Inline allowlisting

### В коде
```python
# Прямо на строке
API_KEY = "secret-value"  # pragma: allowlist secret

# На следующей строке
# pragma: allowlist nextline secret
API_KEY = "secret-value"
```

### Для разных языков
```javascript
// JavaScript
const secret = "value";  // pragma: allowlist secret
```

```yaml
# YAML
password: "secret"  # pragma: allowlist secret
```

## Настройка плагинов

### Посмотреть все плагины
```bash
detect-secrets scan --list-all-plugins
```

### Отключить плагины
```bash
detect-secrets scan --disable-plugin KeywordDetector --disable-plugin AWSKeyDetector
```

### Настроить энтропию
```bash
detect-secrets scan --base64-limit 5.0 --hex-limit 4.0
```

## Полезные команды

### Проверить одну строку
```bash
detect-secrets scan --string "potential-secret-value"
```

### Сканировать только allowlisted
```bash
detect-secrets scan --only-allowlisted
```

### Сравнить два baseline
```bash
detect-secrets audit --diff baseline1 baseline2
```

### Отчет только с реальными секретами
```bash
detect-secrets audit --report --only-real .secrets.baseline
```

## Структура baseline файла

```json
{
  "version": "1.5.0",
  "plugins_used": [
    {"name": "AWSKeyDetector"},
    {"name": "Base64HighEntropyString", "limit": 4.5}
  ],
  "filters_used": [
    {"path": "detect_secrets.filters.heuristic.is_potential_uuid"},
    {"path": "detect_secrets.filters.regex.should_exclude_file", "pattern": ["uv\\.lock$"]}
  ],
  "results": {
    "config.py": [
      {
        "type": "Secret Keyword",
        "filename": "config.py",
        "hashed_secret": "abc123...",  # pragma: allowlist secret
        "is_verified": false,
        "line_number": 10
      }
    ]
  }
}
```

## Типичные ложные срабатывания

### В коде:
- `postgres:postgres` - тестовые пароли
- `localhost:5432` - локальные подключения
- `127.0.0.1` - локальные IP
- `secret_key = "test123"` - тестовые ключи # pragma: allowlist secret
- UUID строки и хеши коммитов

### В документации:
- `"password": "example"` - примеры в README # pragma: allowlist secret
- `"token": "abc123"` - примеры в конфигах # pragma: allowlist secret
- `"hashed_secret": "..."` - структуры JSON # pragma: allowlist secret
- `API_KEY = "your-key-here"` - плейсхолдеры # pragma: allowlist secret

### Быстрое решение:
```bash
# Для текущей ошибки добавь inline:
"hashed_secret": "abc123...",  # pragma: allowlist secret

# Или запусти аудит:
uv run detect-secrets audit .secrets.baseline
```

## Интеграция с CI/CD

```yaml
# GitHub Actions
- name: Detect secrets
  run: |
    detect-secrets scan --baseline .secrets.baseline
    if [ $? -ne 0 ]; then
      echo "New secrets detected!"
      exit 1
    fi
```

## Для Python проектов

Обычно исключают:
- `uv.lock` / `requirements.txt`
- `__pycache__/`
- `htmlcov/`
- `*.pyc`
- `.pytest_cache/`

```bash
detect-secrets scan \
  --exclude-files 'uv\.lock$' \
  --exclude-files '__pycache__/.*' \
  --exclude-files 'htmlcov/.*' \
  > .secrets.baseline
```
