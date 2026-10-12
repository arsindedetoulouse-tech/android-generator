package __PACKAGE__.core.navigation

import androidx.navigation3.runtime.NavKey

/**
 * Marker for every destination key that belongs to this application.
 *
 * Intentionally *not* `sealed`: feature modules depend on `:core:navigation` and declare their own
 * routes, so the set of app routes is assembled across modules and is only known to the composition
 * root. Being an [AppRoute] is what makes a key reachable from [Navigator.navigate], which keeps
 * navigation type safe while still allowing features to contribute destinations independently.
 *
 * Implementations MUST be `@Serializable` so Navigation 3 can save and restore the back stack.
 */
interface AppRoute : NavKey