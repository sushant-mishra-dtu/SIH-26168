package com.sih.idr.demo.ui

import androidx.compose.animation.core.Spring
import androidx.compose.animation.core.spring
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

// ── Type face ───────────────────────────────────────────────────────────────
val InterFamily = FontFamily.SansSerif

enum class ThemeMode {
    LIGHT,
    DARK,
    SYSTEM
}

// ── Design Tokens ───────────────────────────────────────────────────────────
@Immutable
interface IDRPalette {
    val isDark: Boolean
    val primary: Color
    val navGreen: Color
    val statusOk: Color
    val statusWarn: Color
    val statusError: Color
    val bgPrimary: Color
    val bgSheet: Color
    val bgCard: Color
    val textPrimary: Color
    val textSecondary: Color
    val textDim: Color
    val overlayBg: Color
    val border: Color
    val speedLimitRing: Color
    val glassSurface: Color
    val glassBorder: Color
    val glassGlow: Color
}

object IDRLightPalette : IDRPalette {
    override val isDark: Boolean = false
    override val primary = Color(0xFF008CFF)
    override val navGreen = Color(0xFF0F9D58) // Google Maps Navigation Green
    override val statusOk = Color(0xFF34C759)
    override val statusWarn = Color(0xFFFF9F0A)
    override val statusError = Color(0xFFFF3B30)
    override val bgPrimary = Color(0xFFFFFFFF)
    override val bgSheet = Color(0xFFFCF6F0) // Warm light cream
    override val bgCard = Color(0xFFF7F7F7)
    override val textPrimary = Color(0xFF1C1C1E)
    override val textSecondary = Color(0xFF8E8E93)
    override val textDim = Color(0xFFC7C7CC)
    override val overlayBg = Color(0xE6FFFFFF)
    override val border = Color(0xFFE5E7EB)
    override val speedLimitRing = Color(0xFFDC2626)
    override val glassSurface = Color(0xF2FFFFFF)
    override val glassBorder = Color(0x1F000000)
    override val glassGlow = Color.Transparent
}

object IDRDarkPalette : IDRPalette {
    override val isDark: Boolean = true
    override val primary = Color(0xFF38BDF8) // Vibrant sky blue
    override val navGreen = Color(0xFF10B981) // Crisp navigation emerald
    override val statusOk = Color(0xFF34D399)
    override val statusWarn = Color(0xFFFBBF24)
    override val statusError = Color(0xFFF87171)
    override val bgPrimary = Color(0xFF0B0F19) // Deep slate night
    override val bgSheet = Color(0xF20F172A) // Refined dark sheet
    override val bgCard = Color(0xF51E293B) // Slate 800 card
    override val textPrimary = Color(0xFFF8FAFC)
    override val textSecondary = Color(0xFF94A3B8)
    override val textDim = Color(0xFF64748B)
    override val overlayBg = Color(0xE60F172A) // Slate 900 glass
    override val border = Color(0x3338BDF8) // Subtle border
    override val speedLimitRing = Color(0xFFEF4444)
    override val glassSurface = Color(0xF00F172A)
    override val glassBorder = Color(0x2E38BDF8)
    override val glassGlow = Color.Transparent
}

/**
 * Stage 3 "tunnel vision" palette, `docs/UI_UX_NAVIGATION_PLAN.md` section 4 as corrected by
 * section 7.3: it delegates to [IDRDarkPalette] for everything it does not override, so it satisfies
 * the whole [IDRPalette] contract and the accents (cyan, emerald, amber, red) stay the dark
 * palette's. Only the backgrounds go deeper, to hold the 7:1 contrast target against a night map.
 * The tunnel-only colours live on [TunnelTokens] so that other [IDRPalette] implementers do not grow
 * fields nothing outside a tunnel reads.
 */
object IDRTunnelPalette : IDRPalette by IDRDarkPalette {
    override val bgPrimary = Color(0xFF080B11) // Ultra-deep obsidian
    override val bgSheet = Color(0xF20B0F19)   // Ultra-deep glass
    override val bgCard = Color(0xF51E293B)    // Slate 800
    override val glassSurface = Color(0xF2080B11)
    override val glassBorder = Color(0x4D00E5FF)
    override val glassGlow = Color.Transparent
}

/** Colours that only the tunnel corridor and its chrome use. Not part of [IDRPalette] on purpose. */
object TunnelTokens {
    val wallGlow = Color(0x3338BDF8)         // Translucent cyan tube
    val ceilingLamp = Color(0xFFFFE082)      // Warm incandescent lamp
    val roadPavement = Color(0xFF131A29)     // Midnight asphalt
    val exitProgressFill = Color(0xFF0284C7) // Progress bar fill
    val sosAlcoveRed = Color(0xFFEF4444)     // Emergency SOS badge
}

// ── Glassmorphism Modifiers & Helpers ───────────────────────────────────────
/**
 * Clean artifact-free glassmorphic modifier.
 * Synchronous shape clipping, frosted translucent fill, and subtle specular gradient rim border.
 */
fun Modifier.glassmorphic(
    shape: Shape = RoundedCornerShape(20.dp),
    backgroundColor: Color,
    borderWidth: Dp = 1.dp,
    borderColor: Color,
    glowColor: Color = Color.Transparent,
    glowRadius: Dp = 0.dp
): Modifier = this
    .clip(shape)
    .background(backgroundColor)
    .border(borderWidth, borderColor, shape)

fun Modifier.glassmorphic(
    shape: Shape = RoundedCornerShape(20.dp),
    backgroundBrush: Brush,
    borderWidth: Dp = 1.dp,
    borderBrush: Brush,
    glowColor: Color = Color.Transparent,
    glowRadius: Dp = 0.dp
): Modifier = this
    .clip(shape)
    .background(backgroundBrush)
    .border(borderWidth, borderBrush, shape)

fun Modifier.glassmorphic(
    shape: Shape = RoundedCornerShape(20.dp),
    backgroundColor: Color,
    borderWidth: Dp = 1.dp,
    borderBrush: Brush,
    glowColor: Color = Color.Transparent,
    glowRadius: Dp = 0.dp
): Modifier = this
    .clip(shape)
    .background(backgroundColor)
    .border(borderWidth, borderBrush, shape)

fun glassBorderBrush(
    isDark: Boolean,
    primaryColor: Color = Color.White
): Brush {
    return if (isDark) {
        Brush.linearGradient(
            listOf(
                Color.White.copy(alpha = 0.22f),
                primaryColor.copy(alpha = 0.12f),
                Color.White.copy(alpha = 0.05f)
            )
        )
    } else {
        Brush.linearGradient(
            listOf(
                Color.Black.copy(alpha = 0.12f),
                Color.Black.copy(alpha = 0.06f),
                Color.Black.copy(alpha = 0.03f)
            )
        )
    }
}

object IDRColors {
    val current: IDRPalette
        @Composable
        get() = LocalIDRPalette.current

    // Compatibility references
    val Blue            = Color(0xFF008CFF)
    val GreenOk         = Color(0xFF34C759)
    val AmberWarn       = Color(0xFFFF9F0A)
    val RedError        = Color(0xFFFF3B30)
    val NavGreen        = Color(0xFF0F9D58)

    val BgPrimary       = Color(0xFFFFFFFF)
    val BgSheet         = Color(0xFFFCF6F0)
    val BgCard          = Color(0xFFF7F7F7)

    val TextPrimary     = Color(0xFF1C1C1E)
    val TextSecondary   = Color(0xFF8E8E93)
    val TextDim         = Color(0xFFC7C7CC)

    val OverlayBg       = Color(0xCCFFFFFF)
}

val LocalIDRPalette = staticCompositionLocalOf<IDRPalette> { IDRLightPalette }
val LocalIsDarkTheme = staticCompositionLocalOf { false }

private val LightScheme = lightColorScheme(
    primary         = IDRLightPalette.primary,
    onPrimary       = Color.White,
    secondary       = IDRLightPalette.navGreen,
    onSecondary     = Color.White,
    tertiary        = IDRLightPalette.statusWarn,
    background      = IDRLightPalette.bgPrimary,
    surface         = IDRLightPalette.bgSheet,
    surfaceVariant  = IDRLightPalette.bgCard,
    onBackground    = IDRLightPalette.textPrimary,
    onSurface       = IDRLightPalette.textPrimary,
    onSurfaceVariant= IDRLightPalette.textSecondary,
    error           = IDRLightPalette.statusError,
)

private val DarkScheme = darkColorScheme(
    primary         = IDRDarkPalette.primary,
    onPrimary       = Color.Black,
    secondary       = IDRDarkPalette.navGreen,
    onSecondary     = Color.Black,
    tertiary        = IDRDarkPalette.statusWarn,
    background      = IDRDarkPalette.bgPrimary,
    surface         = IDRDarkPalette.bgSheet,
    surfaceVariant  = IDRDarkPalette.bgCard,
    onBackground    = IDRDarkPalette.textPrimary,
    onSurface       = IDRDarkPalette.textPrimary,
    onSurfaceVariant= IDRDarkPalette.textSecondary,
    error           = IDRDarkPalette.statusError,
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

// ── Extended theme tokens ───────────────────────────────────────────────────
@Immutable
data class ExtendedColors(
    val isDark: Boolean = false,
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
fun NavigatorTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    tunnelMode: Boolean = false,
    content: @Composable () -> Unit
) {
    // Tunnel mode overrides the user's day/night choice: the Stage 3 inversion is automatic and is
    // driven by the estimator's state, not by a toggle (plan section 2, Stage 3).
    val palette = when {
        tunnelMode -> IDRTunnelPalette
        darkTheme -> IDRDarkPalette
        else -> IDRLightPalette
    }
    val colorScheme = if (palette.isDark) DarkScheme else LightScheme
    val extendedColors = ExtendedColors(
        isDark = palette.isDark,
        statusOk = palette.statusOk,
        statusWarn = palette.statusWarn,
        statusError = palette.statusError,
        overlayBg = palette.overlayBg,
        textDim = palette.textDim
    )

    CompositionLocalProvider(
        LocalIDRPalette provides palette,
        LocalIsDarkTheme provides palette.isDark,
        LocalExtendedColors provides extendedColors
    ) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography  = NavigatorTypography,
            shapes      = NavigatorShapes,
            content     = content
        )
    }
}
