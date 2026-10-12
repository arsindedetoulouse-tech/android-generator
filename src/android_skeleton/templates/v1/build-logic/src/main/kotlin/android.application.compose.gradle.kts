plugins {
    id("org.jetbrains.kotlin.plugin.compose")
}

extensions.configure<com.android.build.api.dsl.ApplicationExtension> {
    buildFeatures {
        compose = true
    }
}
