plugins {
    id("android.library")
    id("android.orbit")
}

dependencies {
    api(libs.androidx.lifecycle.viewmodel)
    api(libs.orbit.viewmodel)
}