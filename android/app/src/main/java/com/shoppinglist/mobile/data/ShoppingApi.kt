package com.shoppinglist.mobile.data

import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path

interface ShoppingApi {
    @POST("auth/register")
    suspend fun register(@Body request: AuthRequest): TokenResponse

    @POST("auth/login")
    suspend fun login(@Body request: AuthRequest): TokenResponse

    @GET("sync")
    suspend fun sync(@Header("Authorization") authorization: String): SyncResponse

    @POST("lists")
    suspend fun createList(@Header("Authorization") authorization: String, @Body request: ListCreate)

    @PATCH("lists/{listId}")
    suspend fun updateList(
        @Header("Authorization") authorization: String,
        @Path("listId") listId: Int,
        @Body request: ListUpdate
    )

    @DELETE("lists/{listId}")
    suspend fun deleteList(@Header("Authorization") authorization: String, @Path("listId") listId: Int)

    @DELETE("lists/{listId}/items")
    suspend fun clearList(@Header("Authorization") authorization: String, @Path("listId") listId: Int)

    @DELETE("lists/{listId}/items/checked")
    suspend fun clearCheckedItems(@Header("Authorization") authorization: String, @Path("listId") listId: Int)

    @POST("lists/{listId}/copy")
    suspend fun copyList(@Header("Authorization") authorization: String, @Path("listId") listId: Int)

    @GET("lists/{listId}/members")
    suspend fun listMembers(
        @Header("Authorization") authorization: String,
        @Path("listId") listId: Int
    ): MembersResponse

    @POST("lists/{listId}/items")
    suspend fun createItem(
        @Header("Authorization") authorization: String,
        @Path("listId") listId: Int,
        @Body request: ItemCreate
    )

    @POST("lists/{listId}/share")
    suspend fun shareList(
        @Header("Authorization") authorization: String,
        @Path("listId") listId: Int,
        @Body request: ShareRequest
    )

    @POST("lists/{listId}/invite")
    suspend fun createInvite(
        @Header("Authorization") authorization: String,
        @Path("listId") listId: Int
    ): InviteResponse

    @POST("invites/{token}/accept")
    suspend fun acceptInvite(@Header("Authorization") authorization: String, @Path("token") token: String)

    @PATCH("items/{itemId}")
    suspend fun updateItem(
        @Header("Authorization") authorization: String,
        @Path("itemId") itemId: Int,
        @Body request: ItemUpdate
    )

    @DELETE("items/{itemId}")
    suspend fun deleteItem(@Header("Authorization") authorization: String, @Path("itemId") itemId: Int)
}
