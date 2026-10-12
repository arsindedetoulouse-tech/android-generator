plugins {
    id("android.library")
    id("android.library.compose")
    id("android.koin")
    id("android.orbit")
    id("android.library.test")
}

dependencies {
    api(project("__FEATURE_API_MODULE__"))
    api(project(":common:data"))
    api(project(":common:domain"))
    api(project(":common:presentation"))
    api(project(":core:navigation"))
    implementation(project(":core:designsystem"))
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.koin.compose)
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.material3)
    implementation(libs.compose.ui)
}