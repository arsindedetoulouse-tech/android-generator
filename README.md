# android-skeleton

> Russian version of this document: [README.ru.md](README.ru.md).

A CLI that creates clean, multi-module Android applications. Python 3.11 or newer is required; the package itself has no Python runtime dependencies. The Android SDK is only needed to build a generated project.

The template ships `app`, `app:navigation`, `build-logic`, `common:domain`, `common:data`, `common:presentation`, `common:testing`, `core:navigation`, `core:datastore`, `core:designsystem`, plus `feature:home` and `feature:home-api`. The starting screen is created as an ordinary feature, because it is no different from any other destination. Jetpack Compose Material 3, Navigation 3, Orbit MVI, Koin, Gradle Kotlin DSL and a version catalog are configured out of the box. The `presentation` layer with its DI registrations and stub data source lives inside each feature module, while the `domain` and `data` layers live in the shared `common:domain` and `common:data` modules: every feature uses them, so each set of types sits in its own layer package (`domain/<feature>`, `data/<feature>`) and identically named types of different features never collide.

Navigation is built on Navigation 3. `:core:navigation` defines the typed route contract (`AppRoute`), a navigator that is the single place where the back stack changes, and navigation state that survives configuration changes and process death. Routes are declared as `@Serializable` objects implementing `AppRoute`, so the back stack is restored without string constants. `app:navigation` only assembles the graph from tabs: the project has no app-owned destination, because every screen arrives from a feature module.

The data chain is offline-first and identical for every feature. A data source is split into `loadLocal()` (cache in Preferences DataStore), `loadRemote()` and `saveLocal()`; a repository loads remote data, saves it to the cache, and on failure returns the cache — it propagates the error only when there is no cache either. The starting screen shows a centered greeting and a value from the stub `feature/<slug>/src/main/assets/<slug>_stub.json`: the app starts and shows data before a real backend exists, and parsing the response is not tied to a specific JSON shape — when no recognisable `id` is present, the whole response is kept. Android merges the assets of every module into the app, so the stub stays next to its feature while the shared `common:data` module reads it. An error in the state is typed: `error: <Feature>Error?` with the values `Unknown` and `Network`, never an exception message. The starting screen offers no back button: the back stack is at its root there, and the system gesture closes the app. Feature string resource names include the feature slug (`feature_home_title`), otherwise two features would declare the same `feature_title` and one of them would win the resource merge.

The slug `home` is reserved for the starting screen: `add-feature home` is rejected. For a similar feature of your own, use something like `home-settings`.

Android baseline: `compileSdk 37`, `targetSdk 36`, `minSdk 24`, Java/Kotlin toolchain 21, AGP `9.4.1`. The Gradle Wrapper ships with the template. The release variant of the app is built with code shrinking and resource shrinking; the ProGuard rules live in `app/proguard-rules.pro`, so Koin, Navigation 3 and Orbit MVI need no manual entries.

## Installation

For local development from the repository root:

```sh
pipx install -e .
```

An editable install links the environment to the working tree, so changes to the Python code and the template are visible immediately, without reinstalling. A regular `pipx install .` copies the files into the environment, and after editing the template it has to be repeated — otherwise the command keeps running from the old copy. Use the editable install to work on the generator, and the regular one to publish the package.

After the package is published to the chosen Python package index:

```sh
pipx install android-skeleton
```

The package and CLI are named `android-skeleton`, while the GitHub repository is named `android-generator`: these are two different names for the same project, and the version check reads the repository address from the metadata of the installed package.

## Creating a project

`create` generates a project only in the current empty directory. Existing files, including hidden ones, cause a refusal; overwriting is not supported.

```sh
mkdir weather-app
cd weather-app
android-skeleton create \
  --package com.example.weather \
  --application-id com.example.weather
```

When `--name` is not given, the Gradle project name and the app label are taken from the current directory name. `--package` sets the Kotlin/Android namespace and `--application-id` sets the Android application id; both are required.

### Additional options

```sh
mkdir field-notes
cd field-notes
android-skeleton create \
  --package com.example.fieldnotes \
  --application-id com.example.fieldnotes \
  --name "Field Notes" \
  --network \
  --locale ru-RU \
  --locale uz-Latn-UZ \
  --sdk-dir ~/apps/android \
  --git-init \
  --verify
```

- `--name` sets the Gradle project name and the app label.
- `--network` adds `core:network` with a Ktor client, JSON content negotiation, explicit timeouts and a Koin module. Base URL, authentication and request logging are not configurable; the client does not throw on an unsuccessful response by itself, it passes the response to the calling code. The flag also adds the `INTERNET` permission.
- `--locale` accepts repeatable BCP-47 tags, for example `ru-RU` or `uz-Latn-UZ`. The CLI normalizes the case and removes duplicates, creating Android resource qualifiers and `locale_config.xml`. Without selected locales neither those files nor the manifest attribute are added.
- `--git-init` runs `git init` after the files have been generated successfully.
- `--sdk-dir` writes the Android SDK location into the project's `local.properties`. The file is machine-dependent and is not kept under version control.
- `--verify` runs `./gradlew build --no-daemon` after generation. It needs a configured SDK location, installed SDK packages and accepted Android SDK licenses. On a Gradle failure the CLI returns a non-zero exit code and keeps the generated project.
- `--force` does not affect generation and exists for exactly one check: it allows creating a feature in a project whose template this version of the CLI does not support (see "Version checks").

There is no separate flag for `core:datastore`: the module is part of every project, because the local cache of the offline data chain is built on it. The `--datastore` flag was removed together with template `1.1.0`.

Available options can be listed with `android-skeleton create --help`.

## Adding a feature module

The command only supports projects created by a compatible version of `android-skeleton` that contain a valid `.android-skeleton.json`. It accepts a lowercase kebab-case slug, refuses on a name conflict or a changed structure of the mandatory Gradle/Koin files, and rejects the reserved slug `home` with a message saying it is taken by the starting screen.

You can inspect the full plan without writing anything first:

```sh
android-skeleton add-feature user-profile --dry-run
android-skeleton add-feature user-profile
```

For `user-profile` the generator creates `feature:user-profile` with a `presentation` layer and a `di` package, plus a separate `feature:user-profile-api`. The model, the repository interface and the use case go to `common:domain/src/main/kotlin/<package>/domain/userprofile/`, and the data source, its implementation and the repository implementation go to `common:data/src/main/kotlin/<package>/data/userprofile/`. The feature module keeps the ViewModel, the state with the typed error, the screen, the DI registrations and the `user-profile_stub.json` stub. The data source implementation reads the stub through `Context` and caches the model in DataStore, so the feature works offline right after generation. The API module contains only the `UserProfile` route as an `@Serializable` object implementing `AppRoute`; state, ViewModel and Compose types stay inside the feature. Unit tests for the ViewModel (in the feature module) and for the repository (in `common:data`, next to the implementation under test) are created along with the feature and run on the JUnit Platform. Feature string resource names get a prefix from the feature slug (`feature_user_profile_title`), because the resources of all feature modules are merged into the app and identically named strings would overwrite each other. The feature screen draws a "Back" button; for a destination that cannot go back, pass `onBack = null` and no button is drawn. Gradle settings, app dependencies and Koin wiring are updated automatically. Before applying anything the CLI checks the target paths and the registrations; existing files are never overwritten, and a write error rolls back the changes already applied.

The generator does not touch the application sources. The feature exports the navigation tab `userProfileSection` — that is a value of the installer type, not a function, so the list receives `add(userProfileSection)`; a call to `add(userProfileSection())` would pass `Unit` to the list. The CLI prints a ready-made code fragment: the import and the tab addition at the entry point of the installer list. The developer inserts it manually. `START_ROUTE` already points at the generated starting screen, so there is nothing to choose; if the project has to open on another feature, change `START_ROUTE` and `TOP_LEVEL_ROUTES` in `app:navigation/src/main/kotlin/<package>/navigation/AppRoutes.kt`. `--dry-run` shows the created files, the updated files, the integrations and that fragment without changing the project.

The `--verify` flag works for `add-feature` too: after writing the files the CLI runs the project build and reports the result. On a build failure the generated feature is kept. `--sdk-dir` writes the SDK location into `local.properties` of an existing project for both commands.

## Android SDK

Building requires the Android SDK. The CLI determines its location in the same order as the Android Gradle Plugin: `ANDROID_HOME`, then `ANDROID_SDK_ROOT`, then `sdk.dir` from the project's `local.properties`. A directory counts as an SDK only if it contains `platforms` or `platform-tools`, so a wrong variable is caught before the build instead of inside it.

Before a build check the CLI also makes sure the SDK has the platforms for the `compileSdk` declared in the template. The check runs before Gradle starts: if the SDK is not configured or a platform is missing, the CLI reports the reason and how to fix it instead of printing Gradle output.

There are three ways to point at the SDK:

- **The `--sdk-dir` flag** — works with any shell and stores the choice in the project, so the decision is visible both in messages and in the project itself:
  ```sh
  android-skeleton create --package com.example.weather \
    --application-id com.example.weather --sdk-dir /path/to/sdk
  ```
- **An environment variable** — suits the case when there is a single SDK for all projects:
  ```sh
  # zsh
  echo 'export ANDROID_HOME=/path/to/sdk' >> ~/.zshrc
  # bash
  echo 'export ANDROID_HOME=/path/to/sdk' >> ~/.bashrc
  # fish
  echo 'set -x ANDROID_HOME /path/to/sdk' >> ~/.config/fish/config.fish
  ```
  A new terminal is needed afterwards: the current one is already running and will not pick up the variable.
- **Manually** — a `sdk.dir=/path/to/sdk` line in the project's `local.properties`.

The CLI does not choose an SDK for you: a machine can have several, and they are not equivalent. When nothing is configured it lists the variants it found, including one recovered from the location of `adb` in `PATH` — that is the typical picture of a machine where the utilities are available but the variables are not set. If no SDK is installed, the CLI offers to install the command line tools; Android Studio is not required for that. Without `--verify` the CLI limits itself to a short warning and generation goes through.

## Version checks

Before generating, `create` prints the version of the installed CLI and the version of its template, so that the result of generation is unambiguously tied to a known version:

```
android-skeleton 0.3.0 (Android template 1.2.0)
Created Android project 'weather-app' in /home/you/weather-app
```

The CLI then compares the installed version with four sources:

| Source | What is compared | Network needed |
|---|---|---|
| Own constants | the template version in the code, in the manifest and the required CLI version | no |
| Working tree | the version in the sources against the version recorded at install time | no |
| GitHub release | the latest release tag of the repository | yes |
| Package index | the published version of the package | yes |

A mismatch on any of them is printed as a warning with both versions and an update command, and generation continues. When an external source is unavailable, a single line says that the currency could not be confirmed — this does not block work, but without network generation takes a few seconds longer.

The comparison with the working tree only runs when the package is installed from sources: a regular copy of the files has no working tree to compare against.

A refusal is the only thing that stops the work. It happens in `add-feature`, when the project template version does not match the installed CLI version: the feature files would end up where the build does not expect them. The CLI names both versions and offers to recreate the project or to pass `--force`:

```
android-skeleton: error: This project was created by template 1.1.0, but the installed
android-skeleton 0.3.0 ships template 1.2.0.
```

## Template versions

The Android template ships inside the Python package in `src/android_skeleton/templates/`. The CLI version lives in `pyproject.toml`, the template version in `manifest.json`. A created project records the CLI and template versions, the project parameters, the selected options and the list of features in `.android-skeleton.json`; `add-feature` uses that metadata to check compatibility. The features list starts with the slug `home` — that is why adding a feature with that name again is rejected.

Projects created by templates `1.0.0` and `1.1.0` are no longer supported: `add-feature` refuses them with an incompatibility message. In `1.2.0` the `domain` and `data` layers moved from feature modules into `common:domain` and `common:data`, and `:core:datastore` became mandatory, so moving an existing project over by hand also touches its module structure. There is no automatic migration.

## License

The project is distributed under the MIT License: [LICENSE](LICENSE).