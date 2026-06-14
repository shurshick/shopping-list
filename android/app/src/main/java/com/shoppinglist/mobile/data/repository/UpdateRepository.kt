package com.shoppinglist.mobile.data.repository

import android.content.Context
import com.shoppinglist.mobile.BuildConfig
import com.shoppinglist.mobile.data.local.UpdatePreferences
import com.shoppinglist.mobile.data.remote.UpdateApi
import com.shoppinglist.mobile.domain.model.AppUpdateInfo
import com.shoppinglist.mobile.domain.model.VersionComparator
import java.util.concurrent.TimeUnit
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class UpdateRepository(
    context: Context,
    private val preferences: UpdatePreferences = UpdatePreferences(context.applicationContext),
    private val api: UpdateApi = createApi()
) {
    suspend fun checkForUpdate(
        currentVersion: String = BuildConfig.VERSION_NAME,
        force: Boolean = false
    ): AppUpdateInfo? {
        if (!force && !preferences.shouldCheck()) return null
        if (!force) preferences.markChecked()

        return runCatching {
            val release = api.latestRelease()
            val latestVersion = release.tag_name?.takeIf { it.isNotBlank() } ?: return@runCatching null
            val releaseUrl = release.html_url?.takeIf { it.isNotBlank() } ?: return@runCatching null
            val apkUrl = release.assets
                .orEmpty()
                .firstOrNull { asset ->
                    val name = asset.name.orEmpty()
                    name.startsWith("shopping-list-android-") && name.endsWith(".apk")
                }
                ?.browser_download_url
                ?: release.assets.orEmpty().firstOrNull { it.name.orEmpty().endsWith(".apk") }?.browser_download_url

            if (apkUrl.isNullOrBlank()) return@runCatching null
            if (!VersionComparator.isNewer(latestVersion, currentVersion)) return@runCatching null
            if (preferences.isDismissed(latestVersion)) return@runCatching null

            AppUpdateInfo(
                latestVersion = latestVersion,
                currentVersion = currentVersion,
                releaseUrl = releaseUrl,
                apkDownloadUrl = apkUrl,
                releaseName = release.name,
                publishedAt = release.published_at,
                isUpdateAvailable = true
            )
        }.getOrNull()
    }

    fun dismissUpdate(version: String) {
        preferences.dismissVersion(version)
    }

    companion object {
        private fun createApi(): UpdateApi {
            val client = OkHttpClient.Builder()
                .connectTimeout(5, TimeUnit.SECONDS)
                .readTimeout(5, TimeUnit.SECONDS)
                .writeTimeout(5, TimeUnit.SECONDS)
                .addInterceptor { chain ->
                    chain.proceed(
                        chain.request().newBuilder()
                            .header("Accept", "application/vnd.github+json")
                            .header("User-Agent", "shopping-list-android/${BuildConfig.VERSION_NAME}")
                            .build()
                    )
                }
                .build()

            return Retrofit.Builder()
                .baseUrl("https://api.github.com/")
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(UpdateApi::class.java)
        }
    }
}
