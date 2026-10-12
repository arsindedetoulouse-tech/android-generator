pluginManagement {
    includeBuild("build-logic")
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "__PROJECT_NAME__"

include(
    ":app",
    ":app:navigation",
    ":common:data",
    ":common:domain",
    ":common:presentation",
    ":common:testing",
    ":core:designsystem",
    ":core:navigation",
    ":core:datastore",
    ":feature:home",
    ":feature:home-api",__OPTIONAL_MODULE_INCLUDES__
)