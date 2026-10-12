val libs = extensions.getByType<VersionCatalogsExtension>().named("libs")

dependencies {
    add("implementation", libs.findLibrary("orbit-core").get())
    add("implementation", libs.findLibrary("orbit-viewmodel").get())
    add("testImplementation", libs.findLibrary("orbit-test").get())
    add("testImplementation", libs.findLibrary("kotlinx-coroutines-test").get())
}
