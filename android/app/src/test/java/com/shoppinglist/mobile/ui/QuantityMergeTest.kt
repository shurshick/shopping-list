package com.shoppinglist.mobile.ui

import org.junit.Assert.assertEquals
import org.junit.Test

class QuantityMergeTest {
    @Test
    fun addsPlainNumbersAndMatchingUnits() {
        assertEquals("3", mergeQuantities("1", "2"))
        assertEquals("5 kg", mergeQuantities("2 kg", "3 kg"))
        assertEquals("2 kg + 1 pcs", mergeQuantities("2 kg", "1 pcs"))
        assertEquals("2", mergeQuantities("2", ""))
    }
}
