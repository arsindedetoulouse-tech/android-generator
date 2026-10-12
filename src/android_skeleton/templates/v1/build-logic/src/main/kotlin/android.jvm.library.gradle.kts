plugins {
    `java-library`
    kotlin("jvm")
}

kotlin {
    jvmToolchain(21)
}

tasks.withType<Test>().configureEach {
    useJUnitPlatform()
}
