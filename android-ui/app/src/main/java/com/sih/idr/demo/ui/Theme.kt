package com.sih.idr.demo.ui

import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.googlefonts.Font
import androidx.compose.ui.text.googlefonts.GoogleFont
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

// ── Google Fonts ────────────────────────────────────────────────────────────
private val fontProvider = GoogleFont.Provider(
    providerAuthority = "com.google.android.gms.fonts",
    providerPackage = "com.google.android.gms",
    certificates = emptyList()      // works without certs on physical devices
)

private val InterFont = GoogleFont("Inter")

val InterFamily = FontFamily(
    Font(googleFont = InterFont, fontProvider = fontProvider, weight = FontWeight.Light),
    Font(googleFont = InterFont, fontProvider = fontProvider, weight = FontWeight.Normal),
    Font(googleFont = InterFont, fontProvider = fontProvider, weight = FontWeight.Medium),
    Font(googleFont = InterFont, fontProvider = fontProvider, weight = FontWeight.SemiBold),
    Font(googleFont = InterFont, fontProvider = fontProvider, weight = FontWeight.Bold),
    Font(googleFont = InterFont, fontProvider = fontProvider, weight = FontWeight.ExtraBold),
)

// ── Palette ─────────────────────────────────────────────────────────────────
object IDRColors {
    // Brand
    val Blue            = Color(0xFF008CFF)
    
    // Status
    val GreenOk         = Color(0xFF34C759)
    val AmberWarn       = Color(0xFFFF9F0A)
    val RedError        = Color(0xFFFF3B30)

    // Surfaces
    val BgPrimary       = Color(0xFFFFFFFF)
    val BgSheet         = Color(0xFFFCF6F0) // Light warm cream from screenshot
    val BgCard          = Color(0xFFF7F7F7) // Light gray for cards

    // Text
    val TextPrimary     = Color(0xFF1C1C1E)
    val TextSecondary   = Color(0xFF8E8E93)
    val TextDim         = Color(0xFFC7C7CC)

    // Overlay
    val OverlayBg       = Color(0xCCFFFFFF) // Translucent white
}

private val NavigatorColors = lightColorScheme(
    primary         = IDRColors.Blue,
    onPrimary       = Color.White,
    secondary       = IDRColors.GreenOk,
    onSecondary     = Color.White,
    tertiary        = IDRColors.AmberWarn,
    background      = IDRColors.BgPrimary,
    surface         = IDRColors.BgSheet,
    surfaceVariant  = IDRColors.BgCard,
    onBackground    = IDRColors.TextPrimary,
    onSurface       = IDRColors.TextPrimary,
    onSurfaceVariant= IDRColors.TextSecondary,
    error           = IDRColors.RedError,
)

// ── Typography ──────────────────────────────────────────────────────────────
private val NavigatorTypography = Typography(
    displayLarge  = TextStyle(fontFamily = InterFamily, fontWeight = FontWeight.Bold,     fontSize = 34.sp, letterSpacing = (-0.5).sp),
    displayMedium = TextStyle(fontFamily = InterFamily, fontWeight = FontWeight.ExtraBold,fontSize = 28.sp, letterSpacing = (-0.25).sp),
    headlineLarge = TextStyle(fontFamily = InterFamily, fontWeight = FontWeight.SemiBold, fontSize = 24.sp),
    headlineMedium= TextStyle(fontFamily = InterFamily, fontWeight = FontWeight.SemiBold, fontSize = 20.sp),
    titleLarge    = TextStyle(fontFamily = InterFamily, fontWeight = FontWeight.SemiBold, fontSize = 18.sp),
    titleMedium   = TextStyle(fontFamily = InterFamily, fontWeight = FontWeight.Medium,   fontSize = 16.sp),
    titleSmall    = TextStyle(fontFamily = InterFamily, fontWeight = FontWeight.Medium,   fontSize = 14.sp),
    bodyLarge     = TextStyle(fontFamily = InterFamily, fontWeight = FontWeight.Normal,   fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium    = TextStyle(fontFamily = InterFamily, fontWeight = FontWeight.Normal,   fontSize = 14.sp, lineHeight = 20.sp),
    bodySmall     = TextStyle(fontFamily = InterFamily, fontWeight = FontWeight.Normal,   fontSize = 12.sp, lineHeight = 16.sp),
    labelLarge    = TextStyle(fontFamily = InterFamily, fontWeight = FontWeight.Bold,     fontSize = 12.sp, letterSpacing = 1.sp),
    labelMedium   = TextStyle(fontFamily = InterFamily, fontWeight = FontWeight.Bold,     fontSize = 11.sp, letterSpacing = 1.sp),
    labelSmall    = TextStyle(fontFamily = InterFamily, fontWeight = FontWeight.Bold,     fontSize = 10.sp, letterSpacing = 1.sp),
)

// ── Shapes ──────────────────────────────────────────────────────────────────
private val NavigatorShapes = Shapes(
    small       = RoundedCornerShape(8.dp),
    medium      = RoundedCornerShape(14.dp),
    large       = RoundedCornerShape(20.dp),
    extraLarge  = RoundedCornerShape(28.dp),
)

// ── Extended theme tokens (not in Material3) ────────────────────────────────
@Immutable
data class ExtendedColors(
    val statusOk: Color = IDRColors.GreenOk,
    val statusWarn: Color = IDRColors.AmberWarn,
    val statusError: Color = IDRColors.RedError,
    val overlayBg: Color = IDRColors.OverlayBg,
    val textDim: Color = IDRColors.TextDim,
)

val LocalExtendedColors = staticCompositionLocalOf { ExtendedColors() }

// ── Animation specs ─────────────────────────────────────────────────────────
object IDRAnimations {
    val PositionSpring = spring<Float>(dampingRatio = Spring.DampingRatioMediumBouncy, stiffness = Spring.StiffnessLow)
    val SmoothSpring   = spring<Float>(dampingRatio = Spring.DampingRatioNoBouncy, stiffness = Spring.StiffnessMediumLow)
    val SnapSpring     = spring<Float>(dampingRatio = Spring.DampingRatioNoBouncy, stiffness = Spring.StiffnessMedium)
}

// ── Theme Composable ────────────────────────────────────────────────────────
@Composable
fun NavigatorTheme(content: @Composable () -> Unit) {
    androidx.compose.runtime.CompositionLocalProvider(
        LocalExtendedColors provides ExtendedColors()
    ) {
        MaterialTheme(
            colorScheme = NavigatorColors,
            typography  = NavigatorTypography,
            shapes      = NavigatorShapes,
            content     = content
        )
    }
}
