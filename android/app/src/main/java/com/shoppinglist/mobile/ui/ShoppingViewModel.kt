package com.shoppinglist.mobile.ui

import android.app.Application
import android.content.Context
import android.content.SharedPreferences
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.shoppinglist.mobile.data.ApiClient
import com.shoppinglist.mobile.data.ActivityLogDto
import com.shoppinglist.mobile.data.AuthRequest
import com.shoppinglist.mobile.data.ItemCreate
import com.shoppinglist.mobile.data.ItemUpdate
import com.shoppinglist.mobile.data.ListCreate
import com.shoppinglist.mobile.data.ListMemberDto
import com.shoppinglist.mobile.data.ListUpdate
import com.shoppinglist.mobile.data.ShareRequest
import com.shoppinglist.mobile.data.ShoppingItemDto
import com.shoppinglist.mobile.data.ShoppingListDto
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.UUID

data class ShoppingUiState(
    val token: String? = null,
    val serverUrl: String = "",
    val email: String = "",
    val password: String = "",
    val lists: List<ShoppingListDto> = emptyList(),
    val selectedMembers: List<ListMemberDto> = emptyList(),
    val selectedActivity: List<ActivityLogDto> = emptyList(),
    val inviteUrl: String = "",
    val pendingInviteToken: String? = null,
    val productCatalog: List<String> = emptyList(),
    val themeMode: String = "system",
    val selectedListId: Int? = null,
    val pendingOperationCount: Int = 0,
    val canUndoDelete: Boolean = false,
    val isOffline: Boolean = false,
    val lastSuccessfulSync: String? = null,
    val message: String? = null,
    val isLoading: Boolean = false
)

private data class PendingOperation(
    val type: String,
    val clientOperationId: String? = null,
    val listId: Int? = null,
    val itemId: Int? = null,
    val tempId: String? = null,
    val name: String? = null,
    val quantity: String? = null,
    val isChecked: Boolean? = null
)

private data class DeletedItemSnapshot(
    val listId: Int,
    val item: ShoppingItemDto
)

class ShoppingViewModel(application: Application) : AndroidViewModel(application) {
    private val preferences = application.getSharedPreferences("shopping-list", Context.MODE_PRIVATE)
    private val securePreferences = createSecurePreferences(application)
    private val gson = Gson()
    private var pendingOperations = loadPendingOperations()
    private var lastDeletedItem: DeletedItemSnapshot? = null
    private var undoDeleteJob: Job? = null
    private val initialToken = migrateLegacyToken()
    private val defaultProducts = listOf(
        "Хлеб",
        "Молоко",
        "Сыр",
        "Яйца",
        "Масло",
        "Курица",
        "Говядина",
        "Рыба",
        "Картофель",
        "Морковь",
        "Лук",
        "Помидоры",
        "Огурцы",
        "Яблоки",
        "Бананы",
        "Рис",
        "Макароны",
        "Сахар",
        "Соль",
        "Чай",
        "Кофе"
    )
    private val _state = MutableStateFlow(
        ShoppingUiState(
            token = initialToken,
            serverUrl = preferences.getString("serverUrl", "") ?: "",
            lists = loadCachedLists(),
            productCatalog = loadProductCatalog(),
            themeMode = preferences.getString("themeMode", "system") ?: "system",
            selectedListId = preferences.getInt("selectedListId", 0).takeIf { it > 0 },
            pendingOperationCount = pendingOperations.size,
            lastSuccessfulSync = preferences.getString("lastSuccessfulSync", null)
        )
    )
    val state: StateFlow<ShoppingUiState> = _state.asStateFlow()

    init {
        if (_state.value.token != null) {
            sync()
        }
    }

    fun setServerUrl(value: String) = update { copy(serverUrl = value) }
    fun setEmail(value: String) = update { copy(email = value) }
    fun setPassword(value: String) = update { copy(password = value) }

    fun login(register: Boolean = false) = viewModelScope.launch {
        runRequest {
            val current = _state.value
            val api = api()
            val response = if (register) {
                api.register(AuthRequest(current.email, current.password))
            } else {
                api.login(AuthRequest(current.email, current.password))
            }
            securePreferences.edit().putString("token", response.access_token).apply()
            preferences.edit().putString("serverUrl", current.serverUrl.trim()).remove("token").apply()
            _state.value = current.copy(token = response.access_token, password = "", message = null)
            sync()
            _state.value.pendingInviteToken?.let { acceptInvite(it) }
        }
    }

    fun sync() = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        runRequest {
            val api = api()
            replayPendingOperations(api, token)
            val response = api.sync("Bearer $token")
            val selectedListId = _state.value.selectedListId
            val nextSelected = response.lists.firstOrNull { it.id == selectedListId }?.id ?: response.lists.firstOrNull()?.id
            cacheLists(response.lists)
            val syncedAt = localTimestamp()
            preferences.edit().putString("lastSuccessfulSync", syncedAt).apply()
            _state.value = _state.value.copy(
                lists = response.lists,
                selectedListId = nextSelected,
                pendingOperationCount = pendingOperations.size,
                isOffline = false,
                lastSuccessfulSync = syncedAt,
                message = null
            )
            saveSelectedListId(nextSelected)
        }
    }

    fun createList(name: String) = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val operationId = newOperationId()
        val tempId = nextTempId().toString()
        runOnlineThenSync(
            online = {
                api().createList(
                    authorization = "Bearer $token",
                    clientOperationId = operationId,
                    request = ListCreate(name, client_operation_id = operationId, temp_id = tempId)
                )
            },
            offline = {
                enqueue(PendingOperation("create_list", clientOperationId = operationId, tempId = tempId, name = name))
                setOfflineMessage("Список будет создан после восстановления связи")
            }
        )
    }

    fun createItem(name: String, quantity: String) = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val listId = _state.value.selectedListId ?: return@launch
        addCatalogProduct(name)
        val tempItem = ShoppingItemDto(nextTempId(), name, quantity, false, localTimestamp())
        val operationId = newOperationId()
        applyLocalItem(listId, tempItem)
        runOnlineThenSync(
            online = {
                api().createItem(
                    authorization = "Bearer $token",
                    clientOperationId = operationId,
                    listId = listId,
                    request = ItemCreate(
                        name = name,
                        quantity = quantity,
                        is_checked = false,
                        client_operation_id = operationId,
                        temp_id = tempItem.id.toString()
                    )
                )
            },
            offline = {
                enqueue(PendingOperation("create_item", clientOperationId = operationId, listId = listId, itemId = tempItem.id, tempId = tempItem.id.toString(), name = name, quantity = quantity, isChecked = false))
                setOfflineMessage("Товар сохранён на телефоне и отправится при синхронизации")
            }
        )
    }

    fun toggleItem(itemId: Int, checked: Boolean) = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val listId = findListIdForItem(itemId) ?: return@launch
        applyLocalItemUpdate(itemId, isChecked = checked)
        if (itemId < 0) {
            updateQueuedCreatedItem(itemId, isChecked = checked)
            return@launch
        }
        val operationId = newOperationId()
        runOnlineThenSync(
            online = {
                api().updateItem(
                    authorization = "Bearer $token",
                    clientOperationId = operationId,
                    itemId = itemId,
                    request = ItemUpdate(is_checked = checked)
                )
            },
            offline = {
                enqueue(PendingOperation("update_item", clientOperationId = operationId, listId = listId, itemId = itemId, isChecked = checked))
                setOfflineMessage("Изменение сохранено и отправится при синхронизации")
            }
        )
    }

    fun shareList(email: String) = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val listId = _state.value.selectedListId ?: return@launch
        runRequest {
            api().shareList("Bearer $token", listId, ShareRequest(email))
            _state.value = _state.value.copy(message = "Список открыт для $email")
        }
    }

    fun loadMembers() = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val listId = _state.value.selectedListId ?: return@launch
        runRequest {
            val response = api().listMembers("Bearer $token", listId)
            _state.value = _state.value.copy(selectedMembers = response.members)
        }
    }

    fun loadActivity() = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val listId = _state.value.selectedListId ?: return@launch
        runRequest {
            val response = api().listActivity("Bearer $token", listId)
            _state.value = _state.value.copy(selectedActivity = response.events, isOffline = false)
        }
    }

    fun clearListActivity() = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val listId = _state.value.selectedListId ?: return@launch
        runRequest {
            api().clearListActivity("Bearer $token", listId)
            _state.value = _state.value.copy(selectedActivity = emptyList(), isOffline = false, message = "История списка очищена")
        }
    }

    fun renameSelectedList(name: String) = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val listId = _state.value.selectedListId ?: return@launch
        updateLists { lists -> lists.map { if (it.id == listId) it.copy(name = name, updated_at = localTimestamp()) else it } }
        val operationId = newOperationId()
        runOnlineThenSync(
            online = {
                api().updateList(
                    authorization = "Bearer $token",
                    clientOperationId = operationId,
                    listId = listId,
                    request = ListUpdate(name)
                )
            },
            offline = {
                enqueue(PendingOperation("rename_list", clientOperationId = operationId, listId = listId, name = name))
                setOfflineMessage("Переименование отправится при синхронизации")
            }
        )
    }

    fun copySelectedList() = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val listId = _state.value.selectedListId ?: return@launch
        runRequest {
            api().copyList("Bearer $token", listId)
            sync()
        }
    }

    fun deleteSelectedList() = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val listId = _state.value.selectedListId ?: return@launch
        val operationId = newOperationId()
        runOnlineThenSync(
            online = {
                api().deleteList("Bearer $token", operationId, listId)
                _state.value = _state.value.copy(selectedListId = null)
            },
            offline = { setOfflineMessage("Удаление списка доступно после подключения к серверу") }
        )
    }

    fun clearSelectedList() = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val listId = _state.value.selectedListId ?: return@launch
        updateLists { lists -> lists.map { if (it.id == listId) it.copy(items = emptyList(), updated_at = localTimestamp()) else it } }
        val operationId = newOperationId()
        runOnlineThenSync(
            online = { api().clearList("Bearer $token", operationId, listId) },
            offline = {
                enqueue(PendingOperation("clear_list", clientOperationId = operationId, listId = listId))
                setOfflineMessage("Очистка списка отправится при синхронизации")
            }
        )
    }

    fun clearPurchasedItems() = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val listId = _state.value.selectedListId ?: return@launch
        updateLists { lists ->
            lists.map { list ->
                if (list.id == listId) list.copy(items = list.items.filterNot { it.is_checked }, updated_at = localTimestamp()) else list
            }
        }
        val operationId = newOperationId()
        runOnlineThenSync(
            online = { api().clearCheckedItems("Bearer $token", operationId, listId) },
            offline = {
                enqueue(PendingOperation("clear_checked", clientOperationId = operationId, listId = listId))
                setOfflineMessage("Очистка купленных отправится при синхронизации")
            }
        )
    }

    fun restorePurchasedItems() = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val listId = _state.value.selectedListId ?: return@launch
        updateLists { lists ->
            lists.map { list ->
                if (list.id == listId) {
                    list.copy(items = list.items.map { it.copy(is_checked = false, updated_at = localTimestamp()) }, updated_at = localTimestamp())
                } else {
                    list
                }
            }
        }
        val operationId = newOperationId()
        runOnlineThenSync(
            online = { api().restoreCheckedItems("Bearer $token", operationId, listId) },
            offline = {
                enqueue(PendingOperation("restore_checked", clientOperationId = operationId, listId = listId))
                setOfflineMessage("Купленные товары будут возвращены при синхронизации")
            }
        )
    }

    fun updateItem(itemId: Int, name: String, quantity: String) = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val listId = findListIdForItem(itemId) ?: return@launch
        applyLocalItemUpdate(itemId, name = name, quantity = quantity)
        if (itemId < 0) {
            updateQueuedCreatedItem(itemId, name = name, quantity = quantity)
            return@launch
        }
        val operationId = newOperationId()
        runOnlineThenSync(
            online = {
                api().updateItem(
                    authorization = "Bearer $token",
                    clientOperationId = operationId,
                    itemId = itemId,
                    request = ItemUpdate(name = name, quantity = quantity)
                )
            },
            offline = {
                enqueue(PendingOperation("update_item", clientOperationId = operationId, listId = listId, itemId = itemId, name = name, quantity = quantity))
                setOfflineMessage("Изменение товара отправится при синхронизации")
            }
        )
    }

    fun deleteItem(itemId: Int) = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val snapshot = findItemSnapshot(itemId) ?: return@launch
        lastDeletedItem = snapshot
        removeLocalItem(itemId)
        if (itemId < 0) {
            pendingOperations = pendingOperations.filterNot { it.itemId == itemId }
            savePendingOperations()
            showUndoDelete(message = "Товар удалён", updatePendingCount = true)
            return@launch
        }
        val operationId = newOperationId()
        runOnlineThenSync(
            online = { api().deleteItem("Bearer $token", operationId, itemId) },
            offline = {
                enqueue(PendingOperation("delete_item", clientOperationId = operationId, listId = snapshot.listId, itemId = itemId))
                showUndoDelete(message = "Товар удалён. Изменение отправится при синхронизации")
            },
            keepUndo = true
        )
    }

    fun undoDeleteItem() = viewModelScope.launch {
        val deleted = lastDeletedItem ?: return@launch
        val token = _state.value.token ?: return@launch
        undoDeleteJob?.cancel()
        lastDeletedItem = null
        applyLocalItem(deleted.listId, deleted.item.copy(updated_at = localTimestamp()))
        pendingOperations = pendingOperations.filterNot { it.type == "delete_item" && it.itemId == deleted.item.id }
        savePendingOperations()
        if (deleted.item.id < 0) {
            enqueue(
                PendingOperation(
                    "create_item",
                    clientOperationId = newOperationId(),
                    listId = deleted.listId,
                    itemId = deleted.item.id,
                    tempId = deleted.item.id.toString(),
                    name = deleted.item.name,
                    quantity = deleted.item.quantity,
                    isChecked = deleted.item.is_checked
                )
            )
            update { copy(canUndoDelete = false, message = "Удаление отменено") }
            return@launch
        }
        val restoreOperationId = newOperationId()
        val restoreTempId = nextTempId()
        runOnlineThenSync(
            online = {
                api().createItem(
                    authorization = "Bearer $token",
                    clientOperationId = restoreOperationId,
                    listId = deleted.listId,
                    request = ItemCreate(
                        name = deleted.item.name,
                        quantity = deleted.item.quantity,
                        is_checked = deleted.item.is_checked,
                        client_operation_id = restoreOperationId,
                        temp_id = restoreTempId.toString()
                    )
                )
            },
            offline = {
                enqueue(
                    PendingOperation(
                        "create_item",
                        clientOperationId = restoreOperationId,
                        listId = deleted.listId,
                        itemId = restoreTempId,
                        tempId = restoreTempId.toString(),
                        name = deleted.item.name,
                        quantity = deleted.item.quantity,
                        isChecked = deleted.item.is_checked
                    )
                )
                update { copy(canUndoDelete = false, message = "Удаление отменено. Товар восстановится при синхронизации") }
            }
        )
    }

    fun createInviteLink() = viewModelScope.launch {
        val token = _state.value.token ?: return@launch
        val listId = _state.value.selectedListId ?: return@launch
        runRequest {
            val invite = api().createInvite("Bearer $token", listId)
            _state.value = _state.value.copy(inviteUrl = invite.url, message = "Ссылка приглашения создана")
        }
    }

    fun acceptInvite(token: String) = viewModelScope.launch {
        val authToken = _state.value.token
        if (authToken == null) {
            _state.value = _state.value.copy(pendingInviteToken = token, message = "Войдите, чтобы присоединиться к списку")
            return@launch
        }
        runRequest {
            api().acceptInvite("Bearer $authToken", token)
            _state.value = _state.value.copy(pendingInviteToken = null, message = "Вы присоединились к списку")
            sync()
        }
    }

    fun clearInviteUrl() = update { copy(inviteUrl = "") }

    fun addCatalogProduct(name: String) {
        val normalizedName = name.trim()
        if (normalizedName.isBlank()) return
        val catalog = _state.value.productCatalog
        if (catalog.any { it.equals(normalizedName, ignoreCase = true) }) return
        saveProductCatalog((catalog + normalizedName).sortedWith(String.CASE_INSENSITIVE_ORDER))
    }

    fun removeCatalogProduct(name: String) {
        saveProductCatalog(_state.value.productCatalog.filterNot { it == name })
    }

    fun selectList(listId: Int) {
        saveSelectedListId(listId)
        update { copy(selectedListId = listId, selectedMembers = emptyList(), selectedActivity = emptyList(), inviteUrl = "") }
    }

    fun saveServerUrl(serverUrl: String) {
        val trimmedUrl = serverUrl.trim()
        preferences.edit().putString("serverUrl", trimmedUrl).apply()
        update { copy(serverUrl = trimmedUrl, message = "Адрес сервера сохранен") }
    }

    fun saveThemeMode(themeMode: String) {
        val safeThemeMode = if (themeMode in listOf("system", "light", "dark")) themeMode else "system"
        preferences.edit().putString("themeMode", safeThemeMode).apply()
        update { copy(themeMode = safeThemeMode) }
    }

    fun logout() {
        securePreferences.edit().remove("token").apply()
        preferences.edit().remove("token").apply()
        undoDeleteJob?.cancel()
        lastDeletedItem = null
        update {
            copy(
                token = null,
                password = "",
                lists = emptyList(),
                selectedMembers = emptyList(),
                selectedActivity = emptyList(),
                inviteUrl = "",
                pendingInviteToken = null,
                selectedListId = null,
                canUndoDelete = false,
                message = null
            )
        }
    }

    private suspend fun runOnlineThenSync(
        online: suspend () -> Unit,
        offline: () -> Unit,
        keepUndo: Boolean = false
    ) {
        _state.value = _state.value.copy(isLoading = true, message = null)
        try {
            online()
            sync()
            if (!keepUndo) {
                undoDeleteJob?.cancel()
                lastDeletedItem = null
            }
            _state.value = _state.value.copy(canUndoDelete = keepUndo && lastDeletedItem != null)
            if (keepUndo && lastDeletedItem != null) {
                startUndoDeleteTimer()
            }
        } catch (error: Exception) {
            offline()
            _state.value = _state.value.copy(isOffline = true)
        } finally {
            _state.value = _state.value.copy(isLoading = false, pendingOperationCount = pendingOperations.size)
        }
    }

    private suspend fun runRequest(block: suspend () -> Unit) {
        _state.value = _state.value.copy(isLoading = true, message = null)
        try {
            block()
        } catch (error: Exception) {
            _state.value = _state.value.copy(message = error.message ?: "Ошибка", isOffline = true)
        } finally {
            _state.value = _state.value.copy(isLoading = false, pendingOperationCount = pendingOperations.size)
        }
    }

    private suspend fun replayPendingOperations(api: com.shoppinglist.mobile.data.ShoppingApi, token: String) {
        val operations = pendingOperations.map { it.withOperationId() }
        if (operations.isEmpty()) return
        if (operations != pendingOperations) {
            pendingOperations = operations
            savePendingOperations()
        }
        loop@ for (operation in operations) {
            when (operation.type) {
                "create_list" -> {
                    api.createList(
                        authorization = "Bearer $token",
                        clientOperationId = operation.operationId(),
                        request = ListCreate(
                            name = operation.name.orEmpty(),
                            client_operation_id = operation.operationId(),
                            temp_id = operation.tempId ?: operation.itemId?.toString()
                        )
                    )
                }
                "create_item" -> {
                    val listId = operation.listId ?: continue@loop
                    api.createItem(
                        authorization = "Bearer $token",
                        clientOperationId = operation.operationId(),
                        listId = listId,
                        request = ItemCreate(
                            name = operation.name.orEmpty(),
                            quantity = operation.quantity.orEmpty(),
                            is_checked = operation.isChecked == true,
                            client_operation_id = operation.operationId(),
                            temp_id = operation.tempId ?: operation.itemId?.toString()
                        )
                    )
                }
                "update_item" -> {
                    val itemId = operation.itemId ?: continue@loop
                    api.updateItem(
                        authorization = "Bearer $token",
                        clientOperationId = operation.operationId(),
                        itemId = itemId,
                        request = ItemUpdate(name = operation.name, quantity = operation.quantity, is_checked = operation.isChecked)
                    )
                }
                "delete_item" -> {
                    val itemId = operation.itemId ?: continue@loop
                    api.deleteItem("Bearer $token", operation.operationId(), itemId)
                }
                "clear_list" -> {
                    val listId = operation.listId ?: continue@loop
                    api.clearList("Bearer $token", operation.operationId(), listId)
                }
                "clear_checked" -> {
                    val listId = operation.listId ?: continue@loop
                    api.clearCheckedItems("Bearer $token", operation.operationId(), listId)
                }
                "restore_checked" -> {
                    val listId = operation.listId ?: continue@loop
                    api.restoreCheckedItems("Bearer $token", operation.operationId(), listId)
                }
                "rename_list" -> {
                    val listId = operation.listId ?: continue@loop
                    api.updateList(
                        authorization = "Bearer $token",
                        clientOperationId = operation.operationId(),
                        listId = listId,
                        request = ListUpdate(operation.name.orEmpty())
                    )
                }
            }
        }
        pendingOperations = emptyList()
        savePendingOperations()
    }

    private fun enqueue(operation: PendingOperation) {
        pendingOperations = compactOperations(pendingOperations + operation.withOperationId())
        savePendingOperations()
        _state.value = _state.value.copy(pendingOperationCount = pendingOperations.size)
    }

    private fun compactOperations(operations: List<PendingOperation>): List<PendingOperation> {
        val compacted = mutableListOf<PendingOperation>()
        for (operation in operations) {
            val index = compacted.indexOfLast {
                it.type == operation.type && it.listId == operation.listId && it.itemId == operation.itemId
            }
            if (operation.type in listOf("update_item", "rename_list") && index >= 0) {
                compacted[index] = operation
            } else {
                compacted.add(operation)
            }
        }
        return compacted
    }

    private fun updateQueuedCreatedItem(itemId: Int, name: String? = null, quantity: String? = null, isChecked: Boolean? = null) {
        pendingOperations = pendingOperations.map {
            if (it.type == "create_item" && it.itemId == itemId) {
                it.copy(
                    name = name ?: it.name,
                    quantity = quantity ?: it.quantity,
                    isChecked = isChecked ?: it.isChecked
                )
            } else {
                it
            }
        }
        savePendingOperations()
        update { copy(pendingOperationCount = pendingOperations.size) }
    }

    private fun applyLocalItem(listId: Int, item: ShoppingItemDto) {
        updateLists { lists ->
            lists.map { list ->
                if (list.id == listId) {
                    list.copy(items = (list.items.filterNot { it.id == item.id } + item), updated_at = localTimestamp())
                } else {
                    list
                }
            }
        }
    }

    private fun applyLocalItemUpdate(itemId: Int, name: String? = null, quantity: String? = null, isChecked: Boolean? = null) {
        updateLists { lists ->
            lists.map { list ->
                list.copy(
                    items = list.items.map { item ->
                        if (item.id == itemId) {
                            item.copy(
                                name = name ?: item.name,
                                quantity = quantity ?: item.quantity,
                                is_checked = isChecked ?: item.is_checked,
                                updated_at = localTimestamp()
                            )
                        } else {
                            item
                        }
                    }
                )
            }
        }
    }

    private fun removeLocalItem(itemId: Int) {
        updateLists { lists ->
            lists.map { list -> list.copy(items = list.items.filterNot { it.id == itemId }, updated_at = localTimestamp()) }
        }
    }

    private fun updateLists(transform: (List<ShoppingListDto>) -> List<ShoppingListDto>) {
        val lists = transform(_state.value.lists)
        cacheLists(lists)
        _state.value = _state.value.copy(lists = lists)
    }

    private fun findListIdForItem(itemId: Int): Int? {
        return _state.value.lists.firstOrNull { list -> list.items.any { it.id == itemId } }?.id
    }

    private fun findItemSnapshot(itemId: Int): DeletedItemSnapshot? {
        for (list in _state.value.lists) {
            val item = list.items.firstOrNull { it.id == itemId }
            if (item != null) return DeletedItemSnapshot(list.id, item)
        }
        return null
    }

    private fun setOfflineMessage(message: String) {
        update { copy(message = message) }
    }

    private fun update(block: ShoppingUiState.() -> ShoppingUiState) {
        _state.value = _state.value.block()
    }

    private fun createSecurePreferences(context: Context): SharedPreferences {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        return EncryptedSharedPreferences.create(
            context,
            "shopping-list-secure",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    private fun migrateLegacyToken(): String? {
        val encryptedToken = securePreferences.getString("token", null)
        val legacyToken = preferences.getString("token", null)
        if (!legacyToken.isNullOrBlank()) {
            if (encryptedToken.isNullOrBlank()) {
                securePreferences.edit().putString("token", legacyToken).apply()
            }
            preferences.edit().remove("token").apply()
            return encryptedToken ?: legacyToken
        }
        return encryptedToken
    }

    private fun showUndoDelete(message: String, updatePendingCount: Boolean = false) {
        update {
            copy(
                canUndoDelete = true,
                pendingOperationCount = if (updatePendingCount) pendingOperations.size else pendingOperationCount,
                message = message
            )
        }
        startUndoDeleteTimer()
    }

    private fun startUndoDeleteTimer() {
        undoDeleteJob?.cancel()
        undoDeleteJob = viewModelScope.launch {
            delay(5000)
            lastDeletedItem = null
            update { copy(canUndoDelete = false) }
        }
    }

    private fun api() = ApiClient.create(_state.value.serverUrl)

    private fun localTimestamp(): String = java.time.Instant.now().toString()

    private fun newOperationId(): String = UUID.randomUUID().toString()

    private fun PendingOperation.withOperationId(): PendingOperation {
        return if (clientOperationId.isNullOrBlank()) copy(clientOperationId = newOperationId()) else this
    }

    private fun PendingOperation.operationId(): String = clientOperationId ?: newOperationId()

    private fun nextTempId(): Int {
        val nextId = preferences.getInt("nextTempItemId", -1)
        preferences.edit().putInt("nextTempItemId", nextId - 1).apply()
        return nextId
    }

    private fun loadCachedLists(): List<ShoppingListDto> {
        val stored = preferences.getString("cachedLists", null) ?: return emptyList()
        return runCatching {
            val type = object : TypeToken<List<ShoppingListDto>>() {}.type
            gson.fromJson<List<ShoppingListDto>>(stored, type)
        }.getOrDefault(emptyList())
    }

    private fun cacheLists(lists: List<ShoppingListDto>) {
        preferences.edit().putString("cachedLists", gson.toJson(lists)).apply()
    }

    private fun loadPendingOperations(): List<PendingOperation> {
        val stored = preferences.getString("pendingOperations", null) ?: return emptyList()
        return runCatching {
            val type = object : TypeToken<List<PendingOperation>>() {}.type
            gson.fromJson<List<PendingOperation>>(stored, type)
        }.getOrDefault(emptyList())
    }

    private fun savePendingOperations() {
        preferences.edit().putString("pendingOperations", gson.toJson(pendingOperations)).apply()
    }

    private fun saveSelectedListId(listId: Int?) {
        val editor = preferences.edit()
        if (listId == null) {
            editor.remove("selectedListId")
        } else {
            editor.putInt("selectedListId", listId)
        }
        editor.apply()
    }

    private fun loadProductCatalog(): List<String> {
        val stored = preferences.getString("productCatalog", null)
        return stored
            ?.split("\n")
            ?.map { it.trim() }
            ?.filter { it.isNotBlank() }
            ?.distinct()
            ?.sortedWith(String.CASE_INSENSITIVE_ORDER)
            ?: defaultProducts
    }

    private fun saveProductCatalog(catalog: List<String>) {
        val cleanedCatalog = catalog
            .map { it.trim() }
            .filter { it.isNotBlank() }
            .distinct()
            .sortedWith(String.CASE_INSENSITIVE_ORDER)
        preferences.edit().putString("productCatalog", cleanedCatalog.joinToString("\n")).apply()
        _state.value = _state.value.copy(productCatalog = cleanedCatalog)
    }
}
