plugins {
    id("android.library")
    id("android.library.compose")
    id("android.library.test")
}

dependencies {
    api(project(":core:navigation"))
    api(project(":feature:home-api"))
    api(libs.androidx.navigation3.ui)
    implementation(project(":core:designsystem"))
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.material3)
    implementation(libs.compose.ui)
}