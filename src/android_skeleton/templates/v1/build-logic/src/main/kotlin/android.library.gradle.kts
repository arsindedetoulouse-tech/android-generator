plugins {
    id("com.android.library")
}

extensions.configure<com.android.build.api.dsl.LibraryExtension> {
    namespace = moduleNamespace()
    compileSdk = 37
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
    defaultConfig {
        minSdk = 24
    }
}

kotlin {
    jvmToolchain(21)
}

tasks.withType<Test>().configureEach {
    useJUnitPlatform()
}

/**
 * Namespace of this module: the root package shared by all of its sources.
 *
 * Deriving it from the Gradle project path instead produces wrong values for nested modules
 * (`:app:navigation` would become `<base>.app.navigation`) and for API modules (`:feature:x-api`
 * would become `<base>.feature.xapi`), which forces every such module to override `namespace` by
 * hand and silently mismatches the generated `R` class. Sources are authoritative, so they win.
 * Modules without sources fall back to the project path.
 *
 * The shared root is used rather than the package of any single file: a module may hold several
 * packages (`data`, `domain`, `presentation`), and picking the first one alphabetically would put
 * the `R` class into a layer package such as `feature.x.data`.
 */
internal fun Project.moduleNamespace(): String {
    val packages = file("src/main/kotlin")
        .takeIf { it.isDirectory }
        ?.walkTopDown()
        ?.filter { it.isFile && it.extension == "kt" }
        ?.mapNotNull { source ->
            source.useLines { lines ->
                lines.firstOrNull { it.startsWith("package ") }
                    ?.removePrefix("package ")
                    ?.trim()
            }
        }
        ?.filter { it.isNotEmpty() }
        ?.toList()
        .orEmpty()

    if (packages.isNotEmpty()) {
        return packages
            .map { it.split(".") }
            .reduce { common, candidate ->
                common.zip(candidate).takeWhile { (left, right) -> left == right }
                    .map { it.first }
            }
            .joinToString(".")
    }

    val basePackage = providers.gradleProperty("basePackage").get()
    val modulePath = path
        .removePrefix(":")
        .replace(":", ".")
        .replace("-", "")
    return "$basePackage.$modulePath"
}
