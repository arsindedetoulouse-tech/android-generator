package __PACKAGE__.designsystem

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val BrandPrimary = Color(0xFF3A6EA5)
private val BrandPrimaryDark = Color(0xFFA6C8EC)
private val BrandSecondary = Color(0xFF53647A)
private val BrandSecondaryDark = Color(0xFFBAC7DB)
private val BrandTertiary = Color(0xFF6B5778)
private val BrandTertiaryDark = Color(0xFFD7BEE4)
private val BrandError = Color(0xFFBA1A1A)
private val BrandErrorDark = Color(0xFFFFB4AB)
private val NeutralSurfaceLight = Color(0xFFFDFCFF)
private val NeutralSurfaceDark = Color(0xFF1A1C1E)
private val NeutralOnSurfaceLight = Color(0xFF1A1C1E)
private val NeutralOnSurfaceDark = Color(0xFFE2E2E6)

private val LightColors = lightColorScheme(
    primary = BrandPrimary,
    secondary = BrandSecondary,
    tertiary = BrandTertiary,
    error = BrandError,
    surface = NeutralSurfaceLight,
    onSurface = NeutralOnSurfaceLight,
)

private val DarkColors = darkColorScheme(
    primary = BrandPrimaryDark,
    secondary = BrandSecondaryDark,
    tertiary = BrandTertiaryDark,
    error = BrandErrorDark,
    surface = NeutralSurfaceDark,
    onSurface = NeutralOnSurfaceDark,
)

private val AppTypography = Typography()

/**
 * Theme of the application.
 *
 * Screens must style themselves from [MaterialTheme] colors and typography and from the tokens in
 * [AppSpacing] and [AppRadii], so that a change here propagates to every destination.
 */
@Composable
fun AppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = AppTypography,
        content = content,
    )
}