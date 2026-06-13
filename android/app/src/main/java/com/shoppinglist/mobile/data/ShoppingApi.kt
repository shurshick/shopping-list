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
    suspend fun createList(
        @Header("Authorization") authorization: String,
        @Header("X-Client-Operation-Id") clientOperationId: String? = null,
        @Body request: ListCreate
    )

    @PATCH("lists/{listId}")
    suspend fun updateList(
        @Header("Authorization") authorization: String,
        @Header("X-Client-Operation-Id") clientOperationId: String? = null,
        @Path("listId") listId: Int,
        @Body request: ListUpdate
    )

    @DELETE("lists/{listId}")
    suspend fun deleteList(
        @Header("Authorization") authorization: String,
        @Header("X-Client-Operation-Id") clientOperationId: String? = null,
        @Path("listId") listId: Int
    )

    @DELETE("lists/{listId}/items")
    suspend fun clearList(
        @Header("Authorization") authorization: String,
        @Header("X-Client-Operation-Id") clientOperationId: String? = null,
        @Path("listId") listId: Int
    )

    @DELETE("lists/{listId}/items/checked")
    suspend fun clearCheckedItems(
        @Header("Authorization") authorization: String,
        @Header("X-Client-Operation-Id") clientOperationId: String? = null,
        @Path("listId") listId: Int
    )

    @PATCH("lists/{listId}/items/checked")
    suspend fun restoreCheckedItems(
        @Header("Authorization") authorization: String,
        @Header("X-Client-Operation-Id") clientOperationId: String? = null,
        @Path("listId") listId: Int
    )

    @POST("lists/{listId}/copy")
    suspend fun copyList(@Header("Authorization") authorization: String, @Path("listId") listId: Int)

    @GET("lists/{listId}/members")
    suspend fun listMembers(
        @Header("Authorization") authorization: String,
        @Path("listId") listId: Int
    ): MembersResponse

    @GET("lists/{listId}/activity")
    suspend fun listActivity(
        @Header("Authorization") authorization: String,
        @Path("listId") listId: Int
    ): ActivityResponse

    @DELETE("lists/{listId}/activity")
    suspend fun clearListActivity(
        @Header("Authorization") authorization: String,
        @Path("listId") listId: Int
    )

    @POST("lists/{listId}/items")
    suspend fun createItem(
        @Header("Authorization") authorization: String,
        @Header("X-Client-Operation-Id") clientOperationId: String? = null,
        @Path("listId") listId: Int,
        @Body request: ItemCreate
    ): ShoppingItemDto

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
        @Header("X-Client-Operation-Id") clientOperationId: String? = null,
        @Path("itemId") itemId: Int,
        @Body request: ItemUpdate
    )

    @DELETE("items/{itemId}")
    suspend fun deleteItem(
        @Header("Authorization") authorization: String,
        @Header("X-Client-Operation-Id") clientOperationId: String? = null,
        @Path("itemId") itemId: Int
    )
}
