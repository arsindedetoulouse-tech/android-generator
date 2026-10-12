plugins {
    id("android.library")
    id("android.koin")
    id("android.library.test")
}

dependencies {
    api(project(":common:domain"))
    api(project(":core:datastore"))
    implementation(libs.kotlinx.serialization.json)
}