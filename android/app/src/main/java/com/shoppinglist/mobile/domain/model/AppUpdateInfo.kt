package com.shoppinglist.mobile.domain.model

data class AppUpdateInfo(
    val latestVersion: String,
    val currentVersion: String,
    val releaseUrl: String,
    val apkDownloadUrl: String?,
    val releaseName: String?,
    val publishedAt: String?,
    val isUpdateAvailable: Boolean
)
