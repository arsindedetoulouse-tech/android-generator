package __PACKAGE__.core.navigation

import androidx.compose.runtime.mutableStateOf
import androidx.navigation3.runtime.NavBackStack
import androidx.navigation3.runtime.NavKey
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

private data object HomeRoute : AppRoute

private data object SettingsRoute : AppRoute

private data object DetailRoute : AppRoute

class NavigatorTest {

    private fun navigationState(
        homeStack: NavBackStack<NavKey> = NavBackStack(HomeRoute),
        settingsStack: NavBackStack<NavKey> = NavBackStack(SettingsRoute),
    ) = NavigationState(
        startRoute = HomeRoute,
        topLevelRoute = mutableStateOf(HomeRoute),
        backStacks = mapOf(
            HomeRoute to homeStack,
            SettingsRoute to settingsStack,
        ),
    )

    @Test
    fun `navigating to a top level route switches the active stack`() {
        val state = navigationState()

        Navigator(state).navigate(SettingsRoute)

        assertEquals(SettingsRoute, state.topLevelRoute)
    }

    @Test
    fun `navigating to a child route pushes it on the active stack`() {
        val homeStack = NavBackStack<NavKey>(HomeRoute)
        val state = navigationState(homeStack = homeStack)

        Navigator(state).navigate(DetailRoute)

        assertEquals(listOf(HomeRoute, DetailRoute), homeStack.toList())
    }

    @Test
    fun `going back pops the child route and keeps the top level route`() {
        val homeStack = NavBackStack<NavKey>(HomeRoute, DetailRoute)
        val state = navigationState(homeStack = homeStack)

        Navigator(state).goBack()

        assertEquals(listOf(HomeRoute), homeStack.toList())
        assertEquals(HomeRoute, state.topLevelRoute)
    }

    @Test
    fun `going back from another top level route falls back to the start route`() {
        val state = navigationState()
        val navigator = Navigator(state)
        navigator.navigate(SettingsRoute)

        navigator.goBack()

        assertEquals(HomeRoute, state.topLevelRoute)
    }

    @Test
    fun `going back at the start route keeps it and does not throw`() {
        val state = navigationState()

        Navigator(state).goBack()

        assertEquals(HomeRoute, state.topLevelRoute)
    }

    @Test
    fun `going back on an empty stack does not throw`() {
        val state = navigationState(homeStack = NavBackStack())

        Navigator(state).goBack()

        assertEquals(HomeRoute, state.topLevelRoute)
    }

    @Test
    fun `navigating to an unknown top level route is ignored`() {
        val homeStack = NavBackStack<NavKey>(HomeRoute)
        val state = navigationState(homeStack = homeStack)

        Navigator(state).navigate(DetailRoute)
        Navigator(state).navigate(DetailRoute)

        assertEquals(listOf(HomeRoute, DetailRoute, DetailRoute), homeStack.toList())
    }
}