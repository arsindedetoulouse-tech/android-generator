package __PACKAGE__.designsystem

import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/**
 * Spacing scale used by every screen instead of ad-hoc dimensions.
 *
 * Screens read these tokens rather than hardcoding padding, so spacing stays consistent and can be
 * re-tuned centrally.
 */
object AppSpacing {
    val none: Dp = 0.dp
    val extraSmall: Dp = 4.dp
    val small: Dp = 8.dp
    val medium: Dp = 16.dp
    val large: Dp = 24.dp
    val extraLarge: Dp = 32.dp
}

/** Corner radius scale used by surfaces, cards and buttons. */
object AppRadii {
    val small: Dp = 8.dp
    val medium: Dp = 12.dp
    val large: Dp = 20.dp
}