package com.shoppinglist.mobile.domain.model

data class DiagnosticsEndpointStatus(
    val name: String,
    val status: String,
    val details: String = ""
)

data class DiagnosticsCheckResult(
    val live: DiagnosticsEndpointStatus? = null,
    val ready: DiagnosticsEndpointStatus? = null,
    val serverConfig: DiagnosticsEndpointStatus? = null,
    val backendVersion: String? = null,
    val serverAppName: String? = null,
    val setupCompleted: Boolean? = null,
    val allowRegistration: Boolean? = null
)

data class DiagnosticsInfo(
    val appVersion: String,
    val versionCode: Int,
    val packageName: String,
    val androidVersion: String,
    val themeMode: String,
    val serverUrl: String,
    val serverType: String,
    val lastSyncSuccessAt: String?,
    val lastSyncAttemptAt: String?,
    val lastSyncError: String?,
    val pendingOperationsCount: Int,
    val syncStatus: String,
    val checkResult: DiagnosticsCheckResult? = null
) {
    fun toSafeReport(): String {
        val check = checkResult
        return buildString {
            appendLine("Shopping List Diagnostics")
            appendLine("App version: $appVersion")
            appendLine("Version code: $versionCode")
            appendLine("Package: $packageName")
            appendLine("Android: $androidVersion")
            appendLine("Theme: $themeMode")
            appendLine("Server: ${serverUrl.ifBlank { "not set" }}")
            appendLine("Server type: $serverType")
            appendLine("Health live: ${check?.live?.status ?: "not checked"}")
            appendLine("Health ready: ${check?.ready?.status ?: "not checked"}")
            appendLine("Server config: ${check?.serverConfig?.status ?: "not checked"}")
            appendLine("Backend version: ${check?.backendVersion ?: "unknown"}")
            appendLine("Last sync success: ${lastSyncSuccessAt ?: "none"}")
            appendLine("Last sync attempt: ${lastSyncAttemptAt ?: "none"}")
            appendLine("Pending operations: $pendingOperationsCount")
            appendLine("Sync status: $syncStatus")
            appendLine("Last sync error: ${lastSyncError ?: "none"}")
        }
    }
}
