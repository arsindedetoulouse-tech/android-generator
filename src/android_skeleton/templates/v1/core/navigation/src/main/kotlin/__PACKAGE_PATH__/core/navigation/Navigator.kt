package __PACKAGE__.core.navigation

/**
 * Handles navigation events (forward and back) by updating the [NavigationState].
 *
 * This is the only place where the back stack is mutated. The UI observes the state and reacts to
 * it, which keeps navigation unidirectional: events go in, state comes out.
 */
class Navigator(val state: NavigationState) {

    /**
     * Navigate to [route].
     *
     * A top level route switches the active back stack; anything else is pushed onto the currently
     * active stack as a child destination.
     */
    fun navigate(route: AppRoute) {
        if (route in state.backStacks.keys) {
            state.topLevelRoute = route
        } else {
            state.backStacks[state.topLevelRoute]?.add(route)
        }
    }

    /**
     * Navigate back, falling back to the start route's stack when the active stack is at its base.
     *
     * Calling this at the start route is a no-op: the app keeps the start destination so the user can
     * leave through it with a system back gesture, which the activity handles itself. It must not
     * throw, so an empty or unknown active stack is ignored instead of indexing into it.
     */
    fun goBack() {
        val currentStack = state.backStacks[state.topLevelRoute] ?: return
        val currentRoute = currentStack.lastOrNull() ?: return

        if (currentRoute == state.topLevelRoute) {
            state.topLevelRoute = state.startRoute
        } else {
            currentStack.removeLastOrNull()
        }
    }
}