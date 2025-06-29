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
- **Расписание**: PR создаются в нерабочее время (`schedule:nonOfficeHours`)
- **Группировка**: Зависимости группируются по типам (Python, Docker, GitHub Actions)
- **Auto-merge**: Dev зависимости автоматически мерджятся для patch/minor обновлений
- **Semantic commits**: Коммиты в формате conventional commits
- **Lock file maintenance**: Обновление транзитивных зависимостей каждый понедельник

### Метки
Renovate автоматически добавляет метки:
- `dependencies` - для всех PR
- `python` - для Python зависимостей
- `docker` - для Docker образов
- `ci` - для GitHub Actions

### Ограничения
- Максимум 3 PR одновременно
- Максимум 5 веток одновременно

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
