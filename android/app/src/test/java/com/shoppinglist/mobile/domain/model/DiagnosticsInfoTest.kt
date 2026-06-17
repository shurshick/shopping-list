package com.shoppinglist.mobile.domain.model

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DiagnosticsInfoTest {
    @Test
    fun safeReportContainsSyncSummaryAndPendingCount() {
        val report = sampleDiagnosticsInfo().toSafeReport()

        assertTrue(report.contains("Pending operations: 3"))
        assertTrue(report.contains("Last sync error: Сервер недоступен"))
        assertTrue(report.contains("Health live: ok"))
    }

    @Test
    fun safeReportDoesNotContainSensitiveData() {
        val report = sampleDiagnosticsInfo().toSafeReport()

        assertFalse(report.contains("token", ignoreCase = true))
        assertFalse(report.contains("password", ignoreCase = true))
        assertFalse(report.contains("Authorization", ignoreCase = true))
        assertFalse(report.contains("user@example.com", ignoreCase = true))
        assertFalse(report.contains("Молоко", ignoreCase = true))
    }

    private fun sampleDiagnosticsInfo(): DiagnosticsInfo {
        return DiagnosticsInfo(
            appVersion = "1.4.9",
            versionCode = 32,
            packageName = "com.shoppinglist.mobile",
            androidVersion = "14",
            themeMode = "dark",
            serverUrl = "https://shopping.example.com",
            serverType = "custom",
            lastSyncSuccessAt = "2026-06-17T12:00:00Z",
            lastSyncAttemptAt = "2026-06-17T12:01:00Z",
            lastSyncError = "Сервер недоступен",
            pendingOperationsCount = 3,
            syncStatus = "Ожидают отправки 3 действий",
            checkResult = DiagnosticsCheckResult(
                live = DiagnosticsEndpointStatus("health/live", "ok"),
                ready = DiagnosticsEndpointStatus("health/ready", "ok"),
                serverConfig = DiagnosticsEndpointStatus("server-config", "ok"),
                backendVersion = "1.4.9"
            )
        )
    }
}
