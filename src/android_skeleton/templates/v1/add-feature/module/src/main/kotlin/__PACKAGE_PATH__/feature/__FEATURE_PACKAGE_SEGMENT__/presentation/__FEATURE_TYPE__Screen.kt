package __PACKAGE__.feature.__FEATURE_PACKAGE_SEGMENT__.presentation

import __PACKAGE__.designsystem.AppSpacing
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

@Composable
fun __FEATURE_TYPE__Screen(
    state: __FEATURE_TYPE__State,
    onRefresh: () -> Unit,
    // Leave it null for a destination the user cannot leave with a back action, such as a top level
    // destination or the start screen: the screen then hides the button instead of offering one that
    // cannot do anything.
    onBack: (() -> Unit)? = null,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            // The app draws edge to edge, so the screen has to keep its content clear of the
            // status and navigation bars itself.
            .safeDrawingPadding()
            .padding(AppSpacing.large),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.medium),
    ) {
        Text(
            text = stringResource(R.string.__FEATURE_STRING_PREFIX___title),
            style = MaterialTheme.typography.headlineMedium,
        )

        when {
            state.isLoading -> CircularProgressIndicator(
                modifier = Modifier.align(Alignment.CenterHorizontally),
            )

            state.error != null -> Text(
                text = stringResource(R.string.__FEATURE_STRING_PREFIX___error),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error,
            )

            state.model == null -> Text(
                text = stringResource(R.string.__FEATURE_STRING_PREFIX___empty),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            else -> Text(
                text = state.model.id,
                style = MaterialTheme.typography.bodyLarge,
            )
        }

        TextButton(
            onClick = onRefresh,
            enabled = !state.isLoading,
            modifier = Modifier.align(Alignment.End),
        ) {
            Text(text = stringResource(R.string.__FEATURE_STRING_PREFIX___refresh))
        }
        if (onBack != null) {
            TextButton(
                onClick = onBack,
                modifier = Modifier.align(Alignment.End),
            ) {
                Text(text = stringResource(R.string.__FEATURE_STRING_PREFIX___back))
            }
        }
    }
}