plugins {
    id("android.library")
    id("android.library.compose")
}

dependencies {
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.material3)
    implementation(libs.compose.ui)
}
