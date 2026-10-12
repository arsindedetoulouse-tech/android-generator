package __PACKAGE__.feature.__FEATURE_PACKAGE_SEGMENT__.presentation

import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation3.runtime.EntryProviderScope
import androidx.navigation3.runtime.NavKey
import __PACKAGE__.feature.__FEATURE_PACKAGE_SEGMENT__.api.__FEATURE_TYPE__
import org.koin.androidx.compose.koinViewModel

/**
 * The start screen's contribution to the application navigation graph.
 *
 * It differs from a regular feature section in that it raises no back action: the start screen sits at
 * the base of the back stack, and the system back gesture leaves the application. Passing a navigator
 * here would offer a button that cannot do anything.
 */
val __FEATURE_LOWER_CAMEL__Section: EntryProviderScope<NavKey>.() -> Unit = {
    entry<__FEATURE_TYPE__> {
        val viewModel = koinViewModel<__FEATURE_TYPE__ViewModel>()
        __FEATURE_TYPE__Screen(
            state = viewModel.container.stateFlow.collectAsStateWithLifecycle().value,
            onRefresh = viewModel::onRefresh,
        )
    }
}