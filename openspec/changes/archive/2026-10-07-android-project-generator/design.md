# Design

## Context

См. `proposal.md` для мотивации, а `specs/android-project-generator/spec.md` для поведенческих требований. Генератор — отдельный Python 3 CLI, запускаемый через `pipx` из будущей директории проекта. Runtime-зависимости Python не добавляются.

Зафиксированный технический baseline Android-шаблона: Kotlin/JVM и Java toolchain 21; `compileSdk 37`, `targetSdk 36`, `minSdk 24`; Compose Material 3, Navigation Compose, Orbit MVI, Koin, Gradle Kotlin DSL, version catalog и convention plugins. Базовые модули: `app`, `app:navigation`, `build-logic`, `common:domain`, `common:data`, `common:presentation`, `common:testing`, `core:designsystem`. Фичи не зависят друг от друга.

## Goals / Non-Goals

**Goals:**

- Поставлять проверяемые шаблонные файлы с Python-пакетом и сохранять совместимость для уже созданных проектов.
- Генерировать минимальный, собираемый проект и compileable feature scaffold без AppScanner-предметной логики.
- Проверять входы и полный файловый план перед изменениями; ограничивать записи текущим проектом.

**Non-Goals:**

- Скачивать template releases, кэшировать их или поддерживать `--offline` в первой версии.
- Автоматически менять NavHost при создании фичи.
- Генерировать предметную логику, backend endpoints или секреты.
- Поддерживать ручные Android-проекты, не созданные этим генератором.

## Decisions

### CLI и доставка шаблона

CLI распространяется как Python-пакет, устанавливаемый через `pipx`; шаблон включается в package data. Runtime использует стандартную библиотеку Python. `create` читает локальный шаблон через package resources и не обращается к сети. Версии CLI и шаблона идентифицируются отдельно. Установленный пакет содержит таблицу поддерживаемых версий шаблона для `add-feature`; если metadata проекта указывает неподдерживаемую версию, команда отказывает, а не подменяет шаблон последним.

**Альтернатива:** загружать последний GitHub release при каждом `create`. Это откладывается до отдельной версии, чтобы v1 не зависела от сетевого источника и не требовала пока не созданного публичного repository remote.

### Структура генерируемого проекта

Template содержит базовые модули и wiring; каждый получает namespace и package из обязательного `--package`, а `applicationId` задаётся отдельно. `--name` меняет root project name и app label; без него имя выводится из текущей директории. SDK/toolchain значения задаются в convention plugins. Базовая локализация содержит только `values`; повторные `--locale` принимают BCP-47 теги, создают Android resource qualifiers и `locale_config.xml`.

`--network` добавляет нейтральный Ktor client без base URL/auth; `--datastore` добавляет Preferences DataStore. Оба флага добавляют Gradle-зависимости и регистрацию Koin. `--git-init` выполняет `git init` только после проверок и успешного создания файлов. `--verify` запускает wrapper Gradle verification после генерации и требует настроенный Android SDK.

### Метаданные генератора

Корневой файл `.android-skeleton.json` хранит schema version, generator version, template version, базовый package/application ID, root name и включённые опции/фичи. `add-feature` проверяет поддерживаемый schema/template version и согласованность ожидаемых файлов до подготовки плана. Это позволяет распознавать только проекты, созданные известными версиями шаблона.

**Альтернатива:** определять поддержку только по наличию файлов Gradle. Это не отличает пользовательский проект от корректной версии шаблона и ненадёжно при изменениях конфигурации.

### Feature-модуль и публичный контракт

`add-feature <name>` принимает lowercase kebab-case slug, строит package segment удалением дефисов и формирует типы в PascalCase. Создаётся один `feature:<name>` с пакетами `data`, `domain`, `presentation`, компилируемым минимальным вертикальным срезом и DI module. Отдельный `feature:<name>-api` содержит только route contract и аргументы. CLI обновляет Gradle settings, app dependencies, `app:navigation` API dependency и app Koin registration; NavHost остаётся ручной интеграцией.

В feature template/API файлах не экспортируются UI State/Action/SideEffect, DTO, persistence entities или инфраструктурные типы. Общие презентационные элементы ограничены тонким Orbit boilerplate; feature сама определяет loading/error state.

### Планирование и безопасная запись

Перед записью CLI валидирует все значения, разрешает все template resources, строит полный change plan и проверяет целевые пути/регистрации. `--dry-run` печатает план и не пишет. Template entries и итоговые пути разрешаются относительно доверенного root; абсолютные пути, traversal, symlink-escape и конфликты запрещаются.

Изменения сначала подготавливаются во временных файлах в целевых файловых системах. Затем файлы заменяются; backups сохраняются на время операции, чтобы откатить ранее заменённые файлы при обработанной ошибке. Существующие пути не перезаписываются, `--force` отсутствует.

**Альтернатива:** подменять текст простыми глобальными replace. Такой подход не надёжен для Gradle Kotlin DSL и пользовательских изменений; `add-feature` поддерживает только известные версии layout и прекращает работу при неоднозначности.

## Risks / Trade-offs

- [Локальный template обновляется только вместе с новым CLI package] → Фиксировать template version в metadata и выпускать обновления CLI вместе с совместимыми версиями шаблона.
- [Новая версия CLI может не содержать шаблон старого проекта] → Сохранять нужные версии template в package data или явно отказывать, не выполняя неявную миграцию.
- [Падение процесса/питания между заменами файлов может прервать откат] → Использовать временные файлы и backups на той же файловой системе; гарантировать rollback для обработанных ошибок и диагностировать аварийное завершение.
- [Генерация неверно экранирует ввод для Kotlin/XML/Gradle] → Валидировать identifiers до рендеринга, применять контекстное escaping и покрыть опасные значения тестами.
- [Android SDK отсутствует при `--verify`] → Сделать сборку opt-in, проверить наличие wrapper/SDK и явно сообщать причину failure.

## Migration Plan

Генератор публикуется как отдельный Python package для установки `pipx`. Пользователь сначала устанавливает CLI, затем запускает `android-skeleton create` в пустом каталоге. Обновление существующего skeleton не входит в v1; `add-feature` использует только поддерживаемую template version, записанную в metadata проекта.
