# Renovate: Краткий гайд

## Что такое Renovate

**Renovate** - автоматический бот для обновления зависимостей. В отличие от Dependabot, имеет лучшую поддержку современных Python инструментов (`uv`, `pyproject.toml`).

## Быстрый старт

### 1. Активация
```bash
# GitHub App (рекомендуется)
https://github.com/apps/renovate

# Или через GitHub Actions
.github/workflows/renovate.yml
```

### 2. Базовая конфигурация
```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "timezone": "Europe/Moscow"
}
```

## Ключевые возможности

### Автоматическое слияние
```json
{
  "packageRules": [
    {
      "matchDepTypes": ["devDependencies"],
      "matchUpdateTypes": ["patch"],
      "automerge": true
    }
  ]
}
```

### Расписание обновлений
```json
{
  "schedule": ["* 22-23,0-4 * * 1-5"],  // Будни ночью
  "lockFileMaintenance": {
    "schedule": ["before 6am on monday"]
  }
}
```

### Группировка зависимостей
```json
{
  "packageRules": [
    {
      "matchPackageNames": ["fastapi", "starlette", "pydantic"],
      "groupName": "FastAPI Ecosystem"
    }
  ]
}
```

## Настройки безопасности

### Уязвимости
```json
{
  "vulnerabilityAlerts": { "enabled": true },
  "osvVulnerabilityAlerts": true,
  "packageRules": [
    {
      "matchCategories": ["security"],
      "prCreation": "immediate",
      "prPriority": 10
    }
  ]
}
```

### Стабильность
```json
{
  "minimumReleaseAge": "3 days",
  "stabilityDays": 5,
  "respectLatest": true
}
```

## Python/UV специфика

### Поддержка uv
- ✅ Автоматически распознает `uv.lock`
- ✅ Обновляет `pyproject.toml` и `uv.lock` синхронно
- ✅ Поддерживает dependency groups

### Типы зависимостей
```json
{
  "packageRules": [
    {
      "matchDepTypes": ["project.dependencies"],
      "dependencyDashboardApproval": true,
      "stabilityDays": 7
    },
    {
      "matchDepTypes": ["dependency-groups"],
      "matchUpdateTypes": ["patch"],
      "automerge": true
    }
  ]
}
```

## Практические примеры

### Консервативные production-зависимости
```json
{
  "matchDepTypes": ["project.dependencies"],
  "prCreation": "not-pending",
  "dependencyDashboardApproval": true,
  "minimumReleaseAge": "7 days"
}
```

### Агрессивные dev-обновления
```json
{
  "matchDepTypes": ["dependency-groups"],
  "matchUpdateTypes": ["patch"],
  "matchCurrentVersion": "!/^0/",  // Исключить 0.x версии
  "automerge": true
}
```

### Блокировка проблемных пакетов
```json
{
  "matchPackageNames": ["safety"],
  "allowedVersions": "<=3.5.2",
  "enabled": true
}
```

## Мониторинг

### Dependency Dashboard
Создается как GitHub Issue с обзором всех обновлений:
- 📊 Статус всех зависимостей
- ⏸️ Отложенные обновления
- 🔒 Заблокированные пакеты
- 🚨 Уязвимости

### Лимиты
```json
{
  "prConcurrentLimit": 2,        // Макс 2 PR одновременно
  "branchConcurrentLimit": 4     // Макс 4 ветки
}
```

## Troubleshooting

### Renovate не видит зависимости
1. Проверь `managerFilePatterns`
2. Убедись что файлы в git
3. Проверь логи Renovate

### Слишком много PR
```json
{
  "groupName": "Dev Dependencies",
  "schedule": ["* 0-4 * * 1"],   // Только понедельник ночью
  "dependencyDashboardApproval": true
}
```

### Отключить обновления
```json
{
  "matchPackageNames": ["проблемный-пакет"],
  "enabled": false
}
```

## Полезные ссылки

- [Renovate Docs](https://docs.renovatebot.com/)
- [uv Integration](https://docs.astral.sh/uv/guides/integration/dependency-bots/)
- [Configuration Options](https://docs.renovatebot.com/configuration-options/)
- [Package Rules](https://docs.renovatebot.com/configuration-options/#packagerules)
