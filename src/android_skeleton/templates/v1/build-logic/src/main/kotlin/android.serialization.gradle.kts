plugins {
    id("org.jetbrains.kotlin.plugin.serialization")
}

val libs = extensions.getByType<VersionCatalogsExtension>().named("libs")

dependencies {
    add("implementation", libs.findLibrary("kotlinx-serialization-core").get())
}