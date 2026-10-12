# Tasks

## 1. Модуль определения расположения SDK

- [x] 1.1 Создать `src/android_skeleton/sdk.py` (Проверено: `test_resolve_uses_environment_before_local_properties` и `test_resolve_falls_back_to_sdk_dir_of_local_properties`) с признаками SDK и резолвером расположения в порядке `ANDROID_HOME` → `ANDROID_SDK_ROOT` → `sdk.dir` из `local.properties`; проверить, что каждый источник проверяется на признаки SDK, а не на существование каталога
- [x] 1.2 Различать три исхода (Проверено: `test_resolve_reports_no_location_when_nothing_is_configured`, `test_resolve_reports_a_configured_location_that_is_not_an_sdk`, `test_resolve_prefers_a_usable_source_over_an_invalid_earlier_one`): SDK не настроен вовсе, задан, но непригоден, найден и пригоден; проверить тестом, что непригодное значение переменной даёт собственный текст ошибки, а не сообщение о ненастройке
- [x] 1.3 Реализовать подбор кандидатов (Проверено: `test_candidate_is_recovered_from_the_location_of_adb`, `test_candidates_exclude_directories_that_are_not_sdks`, `test_candidate_is_not_recovered_from_an_unrelated_adb_on_path`): восстановление каталога из положения `adb` в `PATH` плюс типовые каталоги для Linux, macOS и Windows, с проверкой каждого на признаки SDK; проверить, что существующий, но не-SDK каталог в кандидаты не попадает
- [x] 1.4 Реализовать чтение требуемых уровней компиляции (Проверено: `test_required_api_levels_come_from_every_convention_plugin`, `test_minor_version_suffix_satisfies_only_its_own_api_level`, `test_installed_levels_accept_minor_versions_and_reject_other_ones`) из всех конвенционных плагинов и сопоставление их с каталогами `platforms`, принимая модульный суффикс и отбрасывая чужой уровень; проверить, что `android-37.0` подходит для `compileSdk = 37`, а `android-36.1` — нет
- [x] 1.5 Реализовать построение текста инструкции (Проверено: `test_setup_message_covers_every_shell_without_reading_shell`, `test_setup_message_offers_a_found_candidate_without_choosing_it`, `test_setup_message_reports_a_rejected_location_separately`): проверенные источники, найденные кандидаты, шаги для zsh, bash, fish и Windows и ссылка на утилиты командной строки без Android Studio; проверить, что текст не зависит от значения `SHELL` и содержит блок каждой оболочки
- [x] 1.6 Реализовать запись `local.properties` (Проверено: `test_write_local_properties_records_the_chosen_directory`, `test_validate_sdk_directory_rejects_unusable_values`) по указанному пути после проверки пригодности; проверить, что непригодный путь не создаёт файл

## 2. Подключение к CLI

- [x] 2.1 Добавить флаг `--sdk-dir` (Проверено: `test_sdk_dir_is_rejected_before_the_project_is_created` — каталог проекта остаётся пустым, `local.properties` не появляется) в `create` и `add-feature` с валидацией пути до любых записей; проверить, что непригодный путь отвергается и файл настроек не появляется
- [x] 2.2 Выполнять предварительную проверку SDK (Проверено: `test_verify_does_not_start_gradle_when_the_sdk_is_unconfigured`; на машине отказ приходит мгновенно вместо 30 секунд и стектрейса Gradle) в начале проверки сборки и не запускать Gradle при провале; проверить тестом, что сборка не запускается, а сообщение называет причину
- [x] 2.3 Добавить проверку требуемых платформ (Проверено: `test_verify_reports_a_missing_platform_before_starting_gradle`) с перечнем требуемого и установленных уровней; проверить тестом на SDK без нужной платформы
- [x] 2.4 Писать предупреждение о ненастроенном SDK (Проверено: `test_generation_warns_about_the_sdk_when_verification_is_not_requested`, `test_warning_names_a_configured_location_that_is_not_an_sdk`, а также два теста на отсутствие предупреждения при настроенном SDK) после генерации, когда проверка сборки не запрошена; проверить, что генерация завершается успешно и выводится предупреждение
- [x] 2.5 Записывать указанное расположение (Проверено: `test_sdk_dir_records_the_location_and_lets_verification_run`, `test_add_feature_records_an_explicit_sdk_location`) в файл настроек проекта перед проверкой сборки; проверить тестом, что файл создан и сборка запускается

## 3. Документация и проверка

- [x] 3.1 Обновить `README.md` (Добавлен раздел «Android SDK» с порядком определения, тремя способами указать путь, примерами для zsh, bash и fish и указанием, что Android Studio не требуется): флаг `--sdk-dir`, порядок определения SDK, варианты для разных оболочек и случай без Android Studio; проверить, что инструкция не требует bash и Studio
- [x] 3.2 Прогнать весь набор (Проверено: `python -m unittest discover -s tests -t tests` — 102 теста, 0 падений; интеграционный прогон с `ANDROID_SKELETON_INTEGRATION=1` проходит за 113 с; `openspec validate android-sdk-preflight --strict` и `validate --specs --strict` зелёные) `python -m unittest discover -s tests -t tests` и `openspec validate android-sdk-preflight --strict`
- [x] 3.3 Проверить на рабочей машине (Проверено: без SDK — предупреждение и мгновенная ошибка до Gradle с перечислением обоих найденных SDK; при непригодном `ANDROID_HOME` — отдельное сообщение; при SDK без платформы 37 — перечень требуемого и установленного; `--sdk-dir /home/yulia/apps/android` — сборка `BUILD SUCCESSFUL` при незаданных переменных): генерация без SDK даёт предупреждение, проверка сборки даёт понятную ошибку вместо вывода Gradle, а `--sdk-dir` с существующим SDK приводит к успешной сборке

## Workflow follow-up

- Архивировать change после выполнения задач и ревью.
- Проверить архивный результат: главная спецификация должна получить изменения требования о проверке компилируемости и новое требование о диагностике окружения SDK.