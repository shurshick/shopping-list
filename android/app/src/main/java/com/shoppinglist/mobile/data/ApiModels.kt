package com.shoppinglist.mobile.data

data class AuthRequest(val email: String, val password: String)
data class TokenResponse(val access_token: String, val token_type: String)
data class HealthStatusDto(
    val status: String = "",
    val version: String? = null,
    val timestamp: String? = null,
    val database: String? = null,
    val migration: String? = null
)

data class ServerConfigDto(
    val app_name: String = "",
    val external_url: String = "",
    val allow_registration: Boolean = false,
    val setup_completed: Boolean = false
)

data class ListCreate(
    val name: String,
    val client_operation_id: String? = null,
    val temp_id: String? = null
)
data class ListUpdate(val name: String)
data class ItemCreate(
    val name: String,
    val quantity: String = "",
    val is_checked: Boolean = false,
    val client_operation_id: String? = null,
    val temp_id: String? = null
)
data class ItemUpdate(val name: String? = null, val quantity: String? = null, val is_checked: Boolean? = null)
data class ShareRequest(val email: String)
data class InviteResponse(val token: String, val url: String, val app_url: String, val expires_at: String? = null)
data class MembersResponse(val members: List<ListMemberDto>)
data class ListMemberDto(val id: Int, val email: String, val is_owner: Boolean)
data class ActivityResponse(val events: List<ActivityLogDto>)
data class ActivityLogDto(
    val id: Int,
    val list_id: Int?,
    val user_id: Int?,
    val user_email: String?,
    val action: String,
    val item_id: Int?,
    val item_name: String,
    val details: String,
    val created_at: String
)

data class SyncResponse(val lists: List<ShoppingListDto>)
data class ShoppingListDto(
    val id: Int,
    val name: String,
    val owner_id: Int,
    val updated_at: String,
    val items: List<ShoppingItemDto>
)

data class ShoppingItemDto(
    val id: Int,
    val name: String,
    val quantity: String,
    val is_checked: Boolean,
    val updated_at: String
)
