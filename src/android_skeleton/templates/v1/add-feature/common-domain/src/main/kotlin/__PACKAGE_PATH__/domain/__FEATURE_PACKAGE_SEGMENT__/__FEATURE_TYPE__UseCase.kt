package __PACKAGE__.domain.__FEATURE_PACKAGE_SEGMENT__

/**
 * Application entry point of the __FEATURE_SLUG__ domain.
 *
 * The ViewModel talks to this use case and never to the repository directly, so business rules added
 * here stay out of the presentation layer.
 */
class __FEATURE_TYPE__UseCase(
    private val repository: __FEATURE_TYPE__Repository,
) {
    suspend operator fun invoke(): __FEATURE_TYPE__Model? = repository.load()
}