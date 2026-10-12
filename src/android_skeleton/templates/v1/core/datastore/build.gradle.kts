plugins {
    id("android.library")
    id("android.koin")
}

dependencies {
    // DataStore types are part of the public contract consumed by feature data sources.
    api(libs.androidx.datastore.preferences)
}
