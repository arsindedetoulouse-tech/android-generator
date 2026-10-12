package __PACKAGE__.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.navigation3.runtime.EntryProviderScope
import androidx.navigation3.runtime.NavEntry
import androidx.navigation3.runtime.NavKey
import androidx.navigation3.runtime.entryProvider

/**
 * A slice of the navigation graph contributed by a feature module.
 *
 * Feature modules expose one of these per feature (see
 * `__PACKAGE__.feature.<segment>.presentation.<feature>Section`). This keeps a feature responsible
 * for its own destinations without knowing anything about the rest of the graph.
 */
typealias EntryProviderInstaller = EntryProviderScope<NavKey>.() -> Unit

/**
 * Assemble the application navigation graph from the slices contributed by the feature modules.
 *
 * There is no app-owned destination: every entry comes from a feature, so adding a destination never
 * requires editing this module.
 *
 * Note that Navigation 3 has no destination hierarchy: nesting comes from the back stacks held by
 * `NavigationState`, not from this provider.
 *
 * @param installers - the graph slices contributed by the feature modules. The caller must pass a
 *   remembered list: this provider is keyed on the list instance, so a freshly built list on every
 *   recomposition would rebuild the whole entry provider on every frame.
 */
@Composable
fun rememberAppEntryProvider(
    installers: List<EntryProviderInstaller>,
): (NavKey) -> NavEntry<NavKey> = remember(installers) {
    entryProvider {
        installers.forEach { installer -> installer() }
    }
}