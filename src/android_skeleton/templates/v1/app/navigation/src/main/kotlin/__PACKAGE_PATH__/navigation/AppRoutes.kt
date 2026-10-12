package __PACKAGE__.navigation

import __PACKAGE__.core.navigation.AppRoute
import __PACKAGE__.feature.home.api.Home

/**
 * The route the app starts on. It is owned by the home feature; this module only references it to
 * declare the start and top level destinations of the application.
 *
 * It must be part of [TOP_LEVEL_ROUTES].
 */
val START_ROUTE: AppRoute = Home

/**
 * Top level routes, each with its own back stack. This is the set a navigation bar would be built
 * from; the currently selected item is `NavigationState.topLevelRoute`.
 */
val TOP_LEVEL_ROUTES: Set<AppRoute> = setOf(Home)