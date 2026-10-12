plugins {
    id("com.android.application")
}

dependencies {
    add("testImplementation", project(":common:testing"))
}