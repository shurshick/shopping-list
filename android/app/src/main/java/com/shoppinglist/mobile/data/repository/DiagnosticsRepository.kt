package com.shoppinglist.mobile.data.repository

import com.shoppinglist.mobile.data.ApiClient
import com.shoppinglist.mobile.domain.model.DiagnosticsCheckResult
import com.shoppinglist.mobile.domain.model.DiagnosticsEndpointStatus
import retrofit2.HttpException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import javax.net.ssl.SSLException

class DiagnosticsRepository {
    suspend fun check(serverUrl: String): DiagnosticsCheckResult {
        if (serverUrl.isBlank()) {
            val status = DiagnosticsEndpointStatus("server", "error", "Укажите адрес сервера")
            return DiagnosticsCheckResult(live = status, ready = status, serverConfig = status)
        }
        val api = ApiClient.create(serverUrl)
        var backendVersion: String? = null
        var appName: String? = null
        var setupCompleted: Boolean? = null
        var allowRegistration: Boolean? = null

        val live = runEndpoint("health/live") {
            val response = api.healthLive()
            backendVersion = response.version ?: backendVersion
            response.status
        }
        val ready = runEndpoint("health/ready") {
            val response = api.healthReady()
            backendVersion = response.version ?: backendVersion
            response.status
        }
        val serverConfig = runEndpoint("server-config") {
            val response = api.serverConfig()
            appName = response.app_name
            setupCompleted = response.setup_completed
            allowRegistration = response.allow_registration
            "ok"
        }

        return DiagnosticsCheckResult(
            live = live,
            ready = ready,
            serverConfig = serverConfig,
            backendVersion = backendVersion,
            serverAppName = appName,
            setupCompleted = setupCompleted,
            allowRegistration = allowRegistration
        )
    }

    private suspend fun runEndpoint(
        name: String,
        request: suspend () -> String
    ): DiagnosticsEndpointStatus {
        return runCatching {
            DiagnosticsEndpointStatus(name = name, status = request().ifBlank { "ok" })
        }.getOrElse { error ->
            DiagnosticsEndpointStatus(name = name, status = "error", details = userFriendlyError(error))
        }
    }

    private fun userFriendlyError(error: Throwable): String {
        return when (error) {
            is UnknownHostException, is ConnectException, is SocketTimeoutException, is SSLException -> {
                "Не удалось подключиться к серверу"
            }
            is HttpException -> when (error.code()) {
                401, 403 -> "Нужен повторный вход"
                in 500..599 -> "Сервер отвечает с ошибкой"
                else -> "Сервер отвечает: HTTP ${error.code()}"
            }
            is IllegalArgumentException -> error.message ?: "Проверьте адрес сервера"
            else -> "Проверьте адрес сервера и интернет-соединение"
        }
    }
}
