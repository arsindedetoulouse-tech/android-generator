plugins {
    id("android.library")
    id("android.library.compose")
    id("android.serialization")
    id("android.library.test")
}

dependencies {
    api(libs.androidx.navigation3.runtime)
    api(libs.androidx.savedstate.compose)
    api(libs.compose.runtime)
    api(libs.compose.runtime.saveable)
}