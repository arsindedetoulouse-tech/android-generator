package __PACKAGE__.core.navigation

import androidx.compose.runtime.ProvidableCompositionLocal
import androidx.compose.runtime.staticCompositionLocalOf

/**
 * The [Navigator] of the enclosing `NavDisplay`.
 *
 * Navigation 3 has no `LocalNavController`: destinations receive navigation events as lambdas, and
 * the only thing that needs to be shared implicitly is the navigator itself. Providing it here lets
 * any destination content raise navigation events without a parameter threaded through the graph.
 */
val LocalNavigator: ProvidableCompositionLocal<Navigator> = staticCompositionLocalOf {
    error("No Navigator provided. Wrap your NavDisplay in CompositionLocalProvider(LocalNavigator provides navigator).")
}