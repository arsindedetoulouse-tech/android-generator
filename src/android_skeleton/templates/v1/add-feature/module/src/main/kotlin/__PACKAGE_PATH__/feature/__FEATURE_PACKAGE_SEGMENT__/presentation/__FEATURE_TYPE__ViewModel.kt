package __PACKAGE__.feature.__FEATURE_PACKAGE_SEGMENT__.presentation

import __PACKAGE__.domain.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__UseCase
import __PACKAGE__.presentation.BaseViewModel
import java.io.IOException
import kotlinx.coroutines.CancellationException
import org.orbitmvi.orbit.syntax.Syntax

class __FEATURE_TYPE__ViewModel(
    private val useCase: __FEATURE_TYPE__UseCase,
) : BaseViewModel<
    __FEATURE_TYPE__State,
    __FEATURE_TYPE__SideEffect,
>(
    initialState = __FEATURE_TYPE__State(),
) {
    init {
        intent { load() }
    }

    fun onRefresh() {
        intent { load() }
    }

    private suspend fun Syntax<__FEATURE_TYPE__State, __FEATURE_TYPE__SideEffect>.load() {
        reduce { state.copy(isLoading = true, error = null) }
        try {
            val model = useCase()
            reduce { state.copy(isLoading = false, model = model, error = null) }
        } catch (cancellation: CancellationException) {
            throw cancellation
        } catch (failure: Exception) {
            reduce {
                state.copy(
                    isLoading = false,
                    error = if (failure is IOException) {
                        __FEATURE_TYPE__Error.Network
                    } else {
                        __FEATURE_TYPE__Error.Unknown
                    },
                )
            }
        }
    }
}