plugins {
    id("android.application")
    id("android.application.compose")
    id("android.koin")
    id("android.application.test")
}

dependencies {
    implementation(project(":app:navigation"))
    implementation(project(":feature:home"))
    implementation(project(":core:designsystem"))
    implementation(project(":core:datastore"))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.navigation3.ui)
    implementation(libs.koin.compose)
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.material3)
    implementation(libs.compose.ui)
__OPTIONAL_APP_DEPENDENCIES__
}