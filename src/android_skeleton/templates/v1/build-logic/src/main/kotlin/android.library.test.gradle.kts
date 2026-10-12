plugins {
    id("android.library")
}

dependencies {
    add("testImplementation", project(":common:testing"))
}