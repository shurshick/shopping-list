package com.shoppinglist.mobile.ui

import com.shoppinglist.mobile.data.ActivityLogDto
import com.shoppinglist.mobile.data.ListMemberDto
import com.shoppinglist.mobile.data.ShoppingItemDto
import com.shoppinglist.mobile.data.ShoppingListDto
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Test

class ShoppingUiStateTest {
    @Test
    fun serverChangeCleanupClearsSensitiveSessionState() {
        val state = ShoppingUiState(
            token = "token",
            serverUrl = "https://old.example.com",
            useTestServer = false,
            customServerUrl = "https://old.example.com",
            email = "user@example.com",
            password = "secret",
            lists = listOf(
                ShoppingListDto(
                    id = 1,
                    name = "Покупки",
                    owner_id = 7,
                    updated_at = "now",
                    items = listOf(
                        ShoppingItemDto(
                            id = 10,
                            name = "Хлеб",
                            quantity = "1",
                            is_checked = false,
                            updated_at = "now"
                        )
                    )
                )
            ),
            selectedMembers = listOf(ListMemberDto(id = 5, email = "other@example.com", is_owner = false)),
            selectedActivity = listOf(
                ActivityLogDto(
                    id = 1,
                    list_id = 1,
                    user_id = 7,
                    user_email = "user@example.com",
                    action = "create_item",
                    item_id = 10,
                    item_name = "Хлеб",
                    details = "created",
                    created_at = "now"
                )
            ),
            inviteUrl = "shoppinglist://join/token",
            pendingInviteToken = "invite-token",
            selectedListId = 1,
            pendingOperationCount = 3,
            canUndoDelete = true,
            isOffline = true,
            lastSuccessfulSync = "2026-06-17 12:00",
            message = "queued"
        )

        val cleared = state.clearedForServerChange()

        assertNull(cleared.token)
        assertEquals("", cleared.password)
        assertEquals(emptyList<ShoppingListDto>(), cleared.lists)
        assertEquals(emptyList<ListMemberDto>(), cleared.selectedMembers)
        assertEquals(emptyList<ActivityLogDto>(), cleared.selectedActivity)
        assertEquals("", cleared.inviteUrl)
        assertNull(cleared.pendingInviteToken)
        assertNull(cleared.selectedListId)
        assertEquals(0, cleared.pendingOperationCount)
        assertFalse(cleared.canUndoDelete)
        assertFalse(cleared.isOffline)
        assertNull(cleared.lastSuccessfulSync)
        assertNull(cleared.message)
        assertEquals("https://old.example.com", cleared.serverUrl)
        assertEquals("https://old.example.com", cleared.customServerUrl)
        assertEquals("user@example.com", cleared.email)
    }

    @Test
    fun fastInputTrimsValueAndRejectsBlank() {
        assertEquals("Молоко 2 л", normalizeFastInput("  Молоко 2 л  "))
        assertNull(normalizeFastInput("   "))
    }

    @Test
    fun defaultListWinsOverLastSelectedWhenAvailable() {
        val lists = listOf(
            ShoppingListDto(id = 1, name = "Дом", owner_id = 1, updated_at = "now", items = emptyList()),
            ShoppingListDto(id = 2, name = "Основной", owner_id = 1, updated_at = "now", items = emptyList())
        )

        val selected = chooseStartupListId(lists, selectedListId = 1, defaultListId = 2)

        assertEquals(2, selected)
    }

    @Test
    fun defaultListFallsBackToSelectedOrFirstAvailable() {
        val lists = listOf(
            ShoppingListDto(id = 1, name = "Дом", owner_id = 1, updated_at = "now", items = emptyList()),
            ShoppingListDto(id = 2, name = "Работа", owner_id = 1, updated_at = "now", items = emptyList())
        )

        assertEquals(1, chooseStartupListId(lists, selectedListId = 1, defaultListId = 99))
        assertEquals(1, chooseStartupListId(lists, selectedListId = 99, defaultListId = 98))
        assertNull(chooseStartupListId(emptyList(), selectedListId = 1, defaultListId = 2))
    }
}
