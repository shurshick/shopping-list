package com.shoppinglist.mobile.domain.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class VersionComparatorTest {
    @Test
    fun newerVersionIsDetected() {
        assertTrue(VersionComparator.isNewer("v1.4.2", "1.4.1"))
        assertTrue(VersionComparator.isNewer("v1.5.0", "1.4.9"))
        assertTrue(VersionComparator.isNewer("v2.0.0", "1.9.9"))
    }

    @Test
    fun equalAndOlderVersionsAreNotUpdates() {
        assertFalse(VersionComparator.isNewer("v1.4.2", "1.4.2"))
        assertFalse(VersionComparator.isNewer("v1.4.1", "1.4.2"))
    }

    @Test
    fun suffixTagsUseNumericVersionOnly() {
        assertEquals(0, VersionComparator.compare("v1.4.2-update-check", "1.4.2"))
        assertFalse(VersionComparator.isNewer("v1.4.2-update-check", "1.4.2"))
    }

    @Test
    fun invalidVersionsAreIgnored() {
        assertEquals(null, VersionComparator.compare("latest", "1.4.2"))
        assertFalse(VersionComparator.isNewer("latest", "1.4.2"))
    }
}
