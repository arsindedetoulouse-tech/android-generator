package __PACKAGE__.feature.__FEATURE_PACKAGE_SEGMENT__.presentation

import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation3.runtime.EntryProviderScope
import androidx.navigation3.runtime.NavKey
import __PACKAGE__.core.navigation.LocalNavigator
import __PACKAGE__.feature.__FEATURE_PACKAGE_SEGMENT__.api.__FEATURE_TYPE__
import org.koin.androidx.compose.koinViewModel

/**
 * This feature's contribution to the application navigation graph. The composition root adds it to
 * the remembered installer list, so the feature stays unaware of the rest of the graph.
 *
 * Declared as a value of the installer type rather than as a function so that the composition root
 * can register it directly as `add(__FEATURE_LOWER_CAMEL__Section)`.
 */
val __FEATURE_LOWER_CAMEL__Section: EntryProviderScope<NavKey>.() -> Unit = {
    entry<__FEATURE_TYPE__> {
        val navigator = LocalNavigator.current
        val viewModel = koinViewModel<__FEATURE_TYPE__ViewModel>()
        __FEATURE_TYPE__Screen(
            state = viewModel.container.stateFlow.collectAsStateWithLifecycle().value,
            onRefresh = viewModel::onRefresh,
            // Pass null for a destination the user cannot leave with a back action, such as a top
            // level destination or the start screen, so the screen hides the button instead of
            // offering one that cannot do anything.
            onBack = { navigator.goBack() },
        )
    }
}