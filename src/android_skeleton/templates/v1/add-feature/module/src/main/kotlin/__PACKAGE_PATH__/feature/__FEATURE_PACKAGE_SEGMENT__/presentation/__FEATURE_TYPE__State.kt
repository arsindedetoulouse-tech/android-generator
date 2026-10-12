package __PACKAGE__.feature.__FEATURE_PACKAGE_SEGMENT__.presentation

import __PACKAGE__.domain.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__Model

data class __FEATURE_TYPE__State(
    val isLoading: Boolean = false,
    val model: __FEATURE_TYPE__Model? = null,
    val error: __FEATURE_TYPE__Error? = null,
)

/**
 * Failure of the __FEATURE_SLUG__ screen the user can act on.
 *
 * The state carries the kind of failure instead of the text of the exception, so the presentation
 * decides what to show and a failure message of the implementation never becomes part of the UI.
 */
enum class __FEATURE_TYPE__Error {
    Unknown,
    Network,
}

sealed interface __FEATURE_TYPE__SideEffect