package __PACKAGE__.core.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.MutableState
import androidx.compose.runtime.Stable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSerializable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshots.SnapshotStateList
import androidx.compose.runtime.toMutableStateList
import androidx.navigation3.runtime.NavBackStack
import androidx.navigation3.runtime.NavEntry
import androidx.navigation3.runtime.NavKey
import androidx.navigation3.runtime.rememberDecoratedNavEntries
import androidx.navigation3.runtime.rememberNavBackStack
import androidx.navigation3.runtime.rememberSaveableStateHolderNavEntryDecorator
import androidx.navigation3.runtime.serialization.NavKeySerializer
import androidx.savedstate.compose.serialization.serializers.MutableStateSerializer

/**
 * Create a navigation state that persists config changes and process death.
 *
 * @param startRoute - the top level route the app starts on. It must also be in [topLevelRoutes].
 * @param topLevelRoutes - the top level routes in the app. The iteration order must be stable
 *   across recompositions, because each route's back stack is remembered in that order.
 */
@Composable
fun rememberAppNavigationState(
    startRoute: AppRoute,
    topLevelRoutes: Set<AppRoute>,
): NavigationState {
    val topLevelRoute = rememberSerializable(
        startRoute,
        topLevelRoutes,
        serializer = MutableStateSerializer(NavKeySerializer<AppRoute>()),
    ) {
        mutableStateOf(startRoute)
    }

    val backStacks = topLevelRoutes.associateWith { key -> rememberNavBackStack(key) }

    // `backStacks` is rebuilt on every recomposition, so it must not be a `remember` key here; the
    // stable inputs are the routes themselves.
    return remember(startRoute, topLevelRoutes) {
        NavigationState(
            startRoute = startRoute,
            topLevelRoute = topLevelRoute,
            backStacks = backStacks,
        )
    }
}

/**
 * State holder for navigation state. This class does not modify its own state; it is designed to be
 * modified by [Navigator].
 *
 * @param startRoute - the start route. The user will exit the app through this route.
 * @param topLevelRoute - the state object backing the current top level route.
 * @param backStacks - the back stack for each top level route.
 */
@Stable
class NavigationState(
    val startRoute: AppRoute,
    topLevelRoute: MutableState<AppRoute>,
    val backStacks: Map<AppRoute, NavBackStack<NavKey>>,
) {
    /** The current top level route. */
    var topLevelRoute: AppRoute by topLevelRoute

    /**
     * The top level routes whose entries should currently be displayed. The start route is always
     * first, so the user always exits the app through it ("exit through home" pattern). At most one
     * other top level route is kept alive; the state of the remaining ones is still retained.
     */
    val stacksInUse: List<AppRoute>
        get() = if (topLevelRoute == startRoute) {
            listOf(startRoute)
        } else {
            listOf(startRoute, topLevelRoute)
        }
}

/**
 * Convert this [NavigationState] into the [NavEntry] list that `NavDisplay` renders. Each back stack
 * gets its own `SaveableStateHolder` decorator, so the state of an entry is retained while it stays
 * in its back stack.
 *
 * The active entry list is memoized on its contents, so `NavDisplay` keeps receiving the same list
 * instance while the back stacks are unchanged and gets a new one when a destination is pushed or
 * popped.
 *
 * Memoizing must key on the resolved entries, not on the back stack: the decorated entries are
 * produced by `rememberDecoratedNavEntries` during this composition, so a `remember` or
 * `derivedStateOf` created with keys that ignore them would keep serving the entries captured on an
 * earlier composition and silently drop every subsequent navigation.
 *
 * @param entryProvider - resolves a key into the content to display for it.
 */
@Composable
fun NavigationState.toEntries(
    entryProvider: (NavKey) -> NavEntry<NavKey>,
): SnapshotStateList<NavEntry<NavKey>> {
    val decoratedEntries = backStacks.mapValues { (_, stack) ->
        val decorators = listOf(
            rememberSaveableStateHolderNavEntryDecorator<NavKey>(),
        )
        rememberDecoratedNavEntries(
            backStack = stack,
            entryDecorators = decorators,
            entryProvider = entryProvider,
        )
    }

    // Reading the decorated entries here subscribes this composition to the back stacks, so pushing
    // or popping re-runs it with fresh entries.
    val activeEntries = stacksInUse.flatMap { route -> decoratedEntries[route].orEmpty() }

    return remember(entryProvider, activeEntries) {
        activeEntries.toMutableStateList()
    }
}