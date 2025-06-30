# Renovate Configuration

Этот проект использует [Renovate](https://renovatebot.com/) для автоматического обновления зависимостей.

## Почему Renovate, а не Dependabot?

Renovate имеет лучшую поддержку uv:
- Автоматически определяет проекты по `uv.lock` файлу
- Обновляет и `pyproject.toml` и `uv.lock`
- Поддерживает inline script metadata
- Может обновлять транзитивные зависимости через `lockFileMaintenance`

## Настройки

### Основные возможности:
- **Расписание**: PR создаются в нерабочее время (`schedule:nonOfficeHours`), а обслуживание lock-файла происходит в понедельник утром.
- **Группировка**: Зависимости интеллектуально группируются по экосистемам (`FastAPI`, `SQLAlchemy`), типам (`production`, `dev`) и платформам (`Docker`, `GitHub Actions`) для уменьшения количества PR.
- **Auto-merge**: Патч-обновления для `dev`-зависимостей сливаются автоматически для минимизации ручного вмешательства. Минорные и мажорные обновления всегда требуют ревью.
- **Semantic commits**: Все коммиты и PR имеют стандартизированные заголовки для чистоты истории.
- **Безопасность**: Уязвимости имеют наивысший приоритет и обрабатываются немедленно, в обход стандартных правил и расписаний.
- **Стабильность**: Для `production`-зависимостей применяется консервативная стратегия с задержкой обновления, чтобы избежать внедрения нестабильных версий.

### Метки
Renovate автоматически добавляет метки:
- `dependencies` - для всех PR
- `python` - для Python зависимостей
- `docker` - для Docker образов
- `ci` - для GitHub Actions

### Ограничения
- Максимум 2 PR одновременно
- Максимум 4 веток одновременно

## Активация

1. **GitHub App**: Установи [Renovate GitHub App](https://github.com/apps/renovate)
2. **Self-hosted**: Или запускай через GitHub Actions/Docker

## Кастомизация

Для изменения настроек редактируй `renovate.json`. Основные опции:

```json
{
  "schedule": ["after 9pm", "before 6am", "every weekend"],
  "automerge": true,
  "labels": ["renovate", "dependencies"],
  "assignees": ["@username"]
}
```

## Inline Script Metadata

Renovate поддерживает обновление зависимостей в Python скриптах с [PEP 723](https://peps.python.org/pep-0723/):

```python
# /// script
# dependencies = [
#   "requests",
#   "rich"
# ]
# ///
```

Для активации добавь в `renovate.json`:
```json
{
  "pep723": {
    "fileMatch": [
      "scripts/*.py"
    ]
  }
}
```

## Мониторинг

- **Dependency Dashboard**: Открывается как issue с обзором всех обновлений
- **PR статусы**: Все проверки CI должны пройти перед мерджем
- **Конфликты**: Renovate автоматически ребейзит PR при конфликтах

## Полезные ссылки

- [Renovate Docs](https://docs.renovatebot.com/)
- [uv Integration Guide](https://docs.astral.sh/uv/guides/integration/dependency-bots/)
- [Configuration Options](https://docs.renovatebot.com/configuration-options/)
