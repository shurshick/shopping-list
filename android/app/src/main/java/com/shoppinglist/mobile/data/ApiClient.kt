package com.shoppinglist.mobile.data

import android.os.Build
import com.shoppinglist.mobile.BuildConfig
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object ApiClient {
    fun create(baseUrl: String): ShoppingApi {
        val clientBuilder = OkHttpClient.Builder()
        clientBuilder.addInterceptor { chain ->
            chain.proceed(
                chain.request().newBuilder()
                    .header("X-Client-App", "shopping-list-android")
                    .header("X-Client-Version", BuildConfig.VERSION_NAME)
                    .header("X-Client-Version-Code", BuildConfig.VERSION_CODE.toString())
                    .header("X-Client-Platform", "android")
                    .header("X-Client-Os-Version", Build.VERSION.RELEASE.orEmpty())
                    .build()
            )
        }
        addDebugLogging(clientBuilder)
        val client = clientBuilder.build()

        return Retrofit.Builder()
            .baseUrl(normalizeBaseUrl(baseUrl))
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ShoppingApi::class.java)
    }

    private fun normalizeBaseUrl(baseUrl: String): String {
        val trimmed = baseUrl.trim()
        return if (trimmed.endsWith("/")) trimmed else "$trimmed/"
    }
}
