package com.shoppinglist.mobile.data.local

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class UpdateCheckPolicyTest {
    @Test
    fun firstRunShouldCheck() {
        assertTrue(UpdateCheckPolicy.shouldCheck(lastCheckAtMillis = 0L, nowMillis = 1000L))
    }

    @Test
    fun recentCheckIsThrottled() {
        assertFalse(
            UpdateCheckPolicy.shouldCheck(
                lastCheckAtMillis = 1000L,
                nowMillis = 1000L + UpdateCheckPolicy.CHECK_INTERVAL_MILLIS - 1L
            )
        )
    }

    @Test
    fun oldCheckAllowsNewRequest() {
        assertTrue(
            UpdateCheckPolicy.shouldCheck(
                lastCheckAtMillis = 1000L,
                nowMillis = 1000L + UpdateCheckPolicy.CHECK_INTERVAL_MILLIS
            )
        )
    }

    @Test
    fun dismissedVersionIsHiddenUntilAnotherVersionAppears() {
        assertTrue(UpdateCheckPolicy.isDismissed("v1.4.2", "v1.4.2"))
        assertFalse(UpdateCheckPolicy.isDismissed("v1.4.2", "v1.4.3"))
    }
}
