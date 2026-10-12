val libs = extensions.getByType<VersionCatalogsExtension>().named("libs")

dependencies {
    add("implementation", libs.findLibrary("koin-android").get())
}
