plugins {
    id("android.jvm.library")
}

dependencies {
    api(libs.junit.jupiter)
    api(libs.junit.platform.launcher)
    api(libs.kotlinx.coroutines.test)
    api(libs.koin.test)
    api(libs.orbit.test)
}