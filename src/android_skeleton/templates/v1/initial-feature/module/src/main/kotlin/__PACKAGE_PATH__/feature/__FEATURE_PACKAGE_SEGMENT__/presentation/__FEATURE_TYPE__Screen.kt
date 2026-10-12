package __PACKAGE__.feature.__FEATURE_PACKAGE_SEGMENT__.presentation

import __PACKAGE__.feature.__FEATURE_PACKAGE_SEGMENT__.R
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import __PACKAGE__.designsystem.AppSpacing

/**
 * Start screen of the application.
 *
 * It is laid out on purpose rather than reusing the shared feature screen: the greeting comes from
 * resources instead of from the data layer, and there is no state meaning "nothing to show" -- the
 * feature ships a data stub, so the start screen always has something to show.
 * Loading, an error and loaded values are still rendered, so the feature's data chain becomes visible
 * as soon as its data source returns something.
 *
 * No back action is offered: the back stack is at its base here, and the system back gesture leaves
 * the application.
 */
@Composable
fun __FEATURE_TYPE__Screen(
    state: __FEATURE_TYPE__State,
    onRefresh: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            // The app draws edge to edge, so the screen has to keep its content clear of the
            // status and navigation bars itself.
            .safeDrawingPadding()
            .padding(AppSpacing.large),
        verticalArrangement = Arrangement.spacedBy(
            AppSpacing.medium,
            Alignment.CenterVertically,
        ),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = stringResource(R.string.__FEATURE_STRING_PREFIX___title),
            style = MaterialTheme.typography.headlineMedium,
            textAlign = TextAlign.Center,
        )

        when {
            state.isLoading -> CircularProgressIndicator()

            state.error != null -> Text(
                text = stringResource(R.string.__FEATURE_STRING_PREFIX___error),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error,
                textAlign = TextAlign.Center,
            )

            state.model != null -> Text(
                text = state.model.id,
                style = MaterialTheme.typography.bodyLarge,
                textAlign = TextAlign.Center,
            )
        }

        Text(
            text = stringResource(R.string.__FEATURE_STRING_PREFIX___hint),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )

        TextButton(
            onClick = onRefresh,
            enabled = !state.isLoading,
        ) {
            Text(text = stringResource(R.string.__FEATURE_STRING_PREFIX___refresh))
        }
    }
}