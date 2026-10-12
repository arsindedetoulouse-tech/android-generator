package __PACKAGE__

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.navigation3.ui.NavDisplay
import __PACKAGE__.core.navigation.LocalNavigator
import __PACKAGE__.core.navigation.Navigator
import __PACKAGE__.core.navigation.rememberAppNavigationState
import __PACKAGE__.core.navigation.toEntries
import __PACKAGE__.designsystem.AppTheme
import __PACKAGE__.feature.home.presentation.homeSection
import __PACKAGE__.navigation.EntryProviderInstaller
import __PACKAGE__.navigation.START_ROUTE
import __PACKAGE__.navigation.TOP_LEVEL_ROUTES
import __PACKAGE__.navigation.rememberAppEntryProvider

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContent {
            AppTheme {
                AppNavDisplay()
            }
        }
    }
}

@Composable
private fun AppNavDisplay() {
    val navigationState = rememberAppNavigationState(
        startRoute = START_ROUTE,
        topLevelRoutes = TOP_LEVEL_ROUTES,
    )
    // Keyed on the navigation state, which is itself remembered from stable inputs. Remembering the
    // navigator without a key would keep it bound to a state object that has since been rebuilt.
    val navigator = remember(navigationState) { Navigator(navigationState) }

    // Every destination comes from a feature. The list must be remembered: the entry provider is
    // keyed on it, so building it inline would rebuild the graph on every recomposition.
    // `add-feature` prints the line to append here for the feature it just generated.
    val installers = remember {
        buildList<EntryProviderInstaller> {
            add(homeSection)
        }
    }

    val entryProvider = rememberAppEntryProvider(installers = installers)

    CompositionLocalProvider(LocalNavigator provides navigator) {
        NavDisplay(
            entries = navigationState.toEntries(entryProvider),
            onBack = { navigator.goBack() },
        )
    }
}