package com.shoppinglist.mobile.data.remote

import retrofit2.http.GET

interface UpdateApi {
    @GET("repos/shurshick/shopping-list/releases/latest")
    suspend fun latestRelease(): GitHubReleaseDto
}

data class GitHubReleaseDto(
    val tag_name: String?,
    val html_url: String?,
    val name: String?,
    val published_at: String?,
    val assets: List<GitHubReleaseAssetDto>?
)

data class GitHubReleaseAssetDto(
    val name: String?,
    val browser_download_url: String?
)
