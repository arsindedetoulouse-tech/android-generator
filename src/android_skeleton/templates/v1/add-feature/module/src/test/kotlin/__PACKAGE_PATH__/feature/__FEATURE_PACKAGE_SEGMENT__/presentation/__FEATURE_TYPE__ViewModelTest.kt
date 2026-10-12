package __PACKAGE__.feature.__FEATURE_PACKAGE_SEGMENT__.presentation

import __PACKAGE__.domain.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__Model
import __PACKAGE__.domain.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__Repository
import __PACKAGE__.domain.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__UseCase
import java.io.IOException
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Test
import org.orbitmvi.orbit.test.testWithInternalState

private class FakeRepository(
    private val result: () -> __FEATURE_TYPE__Model?,
) : __FEATURE_TYPE__Repository {
    override suspend fun load(): __FEATURE_TYPE__Model? = result()
}

class __FEATURE_TYPE__ViewModelTest {

    @Test
    fun `loading moves through the loading state and ends with the model`() = runTest {
        val repository = FakeRepository { __FEATURE_TYPE__Model(id = "42") }

        __FEATURE_TYPE__ViewModel(
            __FEATURE_TYPE__UseCase(repository),
        ).testWithInternalState(this) {
            containerHost.onRefresh()

            expectInternalState { copy(isLoading = true) }
            expectInternalState {
                copy(isLoading = false, model = __FEATURE_TYPE__Model(id = "42"))
            }
        }
    }

    @Test
    fun `a failure is reported as state instead of being thrown`() = runTest {
        val repository = FakeRepository { throw IllegalStateException("offline") }

        __FEATURE_TYPE__ViewModel(
            __FEATURE_TYPE__UseCase(repository),
        ).testWithInternalState(this) {
            containerHost.onRefresh()

            expectInternalState { copy(isLoading = true) }
            expectInternalState { copy(isLoading = false, error = __FEATURE_TYPE__Error.Unknown) }
        }
    }

    @Test
    fun `a network failure is reported as a network error`() = runTest {
        val repository = FakeRepository { throw IOException("no route to host") }

        __FEATURE_TYPE__ViewModel(
            __FEATURE_TYPE__UseCase(repository),
        ).testWithInternalState(this) {
            containerHost.onRefresh()

            expectInternalState { copy(isLoading = true) }
            expectInternalState { copy(isLoading = false, error = __FEATURE_TYPE__Error.Network) }
        }
    }

    @Test
    fun `an empty result is neither loading nor an error`() = runTest {
        val repository = FakeRepository { null }

        __FEATURE_TYPE__ViewModel(
            __FEATURE_TYPE__UseCase(repository),
        ).testWithInternalState(this) {
            containerHost.onRefresh()

            expectInternalState { copy(isLoading = true) }
            expectInternalState { copy(isLoading = false) }
        }
    }

    @Test
    fun `a refresh clears the previous error`() = runTest {
        var failing = true
        val repository = FakeRepository {
            if (failing) throw IllegalStateException("offline")
            __FEATURE_TYPE__Model(id = "42")
        }

        __FEATURE_TYPE__ViewModel(
            __FEATURE_TYPE__UseCase(repository),
        ).testWithInternalState(this) {
            containerHost.onRefresh()

            expectInternalState { copy(isLoading = true) }
            expectInternalState { copy(isLoading = false, error = __FEATURE_TYPE__Error.Unknown) }

            failing = false
            containerHost.onRefresh()

            expectInternalState { copy(isLoading = true, error = null) }
            expectInternalState {
                copy(
                    isLoading = false,
                    model = __FEATURE_TYPE__Model(id = "42"),
                    error = null,
                )
            }
        }
    }
}