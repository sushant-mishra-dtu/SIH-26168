package com.sih.idr.demo.ui

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.spring
import androidx.compose.foundation.gestures.detectVerticalDragGestures
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import kotlin.math.abs

/** Which way a card leaves the screen when swiped. */
enum class SwipeDirection { UP, DOWN }

/**
 * Lets a floating card be thrown off screen with a vertical swipe. The card follows the finger
 * (only in [direction]; the other way is damped), fades as it goes, and either springs back or,
 * past [threshold], calls [onDismissed]. The caller removes it from composition on that call, so
 * nothing here needs to animate the card fully out.
 */
fun Modifier.swipeToDismiss(
    direction: SwipeDirection,
    threshold: Dp = 72.dp,
    onDismissed: () -> Unit
): Modifier = composed {
    val scope = rememberCoroutineScope()
    val offset = remember { Animatable(0f) }
    val thresholdPx = with(LocalDensity.current) { threshold.toPx() }
    val sign = if (direction == SwipeDirection.DOWN) 1f else -1f

    this
        .graphicsLayer {
            translationY = offset.value
            // Fade over twice the threshold so the card is still legible at the decision point.
            alpha = (1f - abs(offset.value) / (thresholdPx * 2f)).coerceIn(0.2f, 1f)
        }
        .pointerInput(direction, onDismissed) {
            detectVerticalDragGestures(
                onDragEnd = {
                    if (offset.value * sign > thresholdPx) {
                        onDismissed()
                    } else {
                        scope.launch { offset.animateTo(0f, spring(stiffness = 500f)) }
                    }
                },
                onDragCancel = {
                    scope.launch { offset.animateTo(0f, spring(stiffness = 500f)) }
                },
                onVerticalDrag = { change, dragAmount ->
                    change.consume()
                    val next = offset.value + dragAmount
                    // Pulling the wrong way is allowed a little, with resistance, so the card
                    // feels attached rather than pinned.
                    val clamped = if (next * sign < 0f) next * 0.25f else next
                    scope.launch { offset.snapTo(clamped) }
                }
            )
        }
}

/**
 * A short vertical swipe as a command, for a control that expands one way and collapses the
 * other. Nothing moves with the finger; the caller animates the state change it already has.
 * The distance is judged at release so a jittery finger does not fire both ways.
 */
fun Modifier.verticalSwipe(
    threshold: Dp = 32.dp,
    onSwipeUp: () -> Unit,
    onSwipeDown: () -> Unit
): Modifier = composed {
    val thresholdPx = with(LocalDensity.current) { threshold.toPx() }
    var travelled = 0f
    this.pointerInput(onSwipeUp, onSwipeDown) {
        detectVerticalDragGestures(
            onDragStart = { travelled = 0f },
            onDragEnd = {
                when {
                    travelled < -thresholdPx -> onSwipeUp()
                    travelled > thresholdPx -> onSwipeDown()
                }
            },
            onVerticalDrag = { change, dragAmount ->
                change.consume()
                travelled += dragAmount
            }
        )
    }
}
