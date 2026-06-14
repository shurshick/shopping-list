package com.shoppinglist.mobile

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.clickable
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CleaningServices
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Logout
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Storefront
import androidx.compose.material.icons.filled.Undo
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import com.shoppinglist.mobile.BuildConfig
import com.shoppinglist.mobile.data.repository.UpdateRepository
import com.shoppinglist.mobile.domain.model.AppUpdateInfo
import com.shoppinglist.mobile.ui.ShoppingUiState
import com.shoppinglist.mobile.ui.ShoppingViewModel
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private val viewModel: ShoppingViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleInviteIntent(intent)
        setContent {
            val state by viewModel.state.collectAsState()
            val useDarkTheme = when (state.themeMode) {
                "dark" -> true
                "light" -> false
                else -> isSystemInDarkTheme()
            }
            MaterialTheme(colorScheme = if (useDarkTheme) darkColorScheme() else lightColorScheme()) {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    if (state.token == null) {
                        LoginScreen(
                            state,
                            viewModel::setServerUrl,
                            viewModel::setEmail,
                            viewModel::setPassword,
                            viewModel::login
                        )
                    } else {
                        ShoppingScreen(
                            state,
                            viewModel::sync,
                            viewModel::selectList,
                            viewModel::createList,
                            viewModel::createItem,
                            viewModel::toggleItem,
                            viewModel::deleteItem,
                            viewModel::shareList,
                            viewModel::loadMembers,
                            viewModel::loadActivity,
                            viewModel::clearListActivity,
                            viewModel::renameSelectedList,
                            viewModel::copySelectedList,
                            viewModel::deleteSelectedList,
                            viewModel::clearSelectedList,
                            viewModel::clearPurchasedItems,
                            viewModel::restorePurchasedItems,
                            viewModel::updateItem,
                            viewModel::undoDeleteItem,
                            viewModel::createInviteLink,
                            viewModel::clearInviteUrl,
                            viewModel::addCatalogProduct,
                            viewModel::removeCatalogProduct,
                            viewModel::saveServerUrl,
                            viewModel::saveThemeMode,
                            viewModel::logout
                        )
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleInviteIntent(intent)
    }

    private fun handleInviteIntent(intent: Intent?) {
        val data = intent?.data ?: return
        if (data.scheme == "shoppinglist" && data.host == "join") {
            val token = data.pathSegments.firstOrNull()
            if (!token.isNullOrBlank()) {
                viewModel.acceptInvite(token)
            }
        }
    }
}

@Composable
private fun LoginScreen(
    state: ShoppingUiState,
    onServerUrl: (String) -> Unit,
    onEmail: (String) -> Unit,
    onPassword: (String) -> Unit,
    onLogin: (Boolean) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(20.dp),
        verticalArrangement = Arrangement.Center
    ) {
        Text("Список покупок", style = MaterialTheme.typography.headlineMedium)
        Text("Войдите или создайте аккаунт", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Spacer(Modifier.height(24.dp))
        OutlinedTextField(
            state.serverUrl,
            onServerUrl,
            label = { Text("Адрес сервера") },
            placeholder = { Text("https://shopping.example.com") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(state.email, onEmail, label = { Text("Email") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
        Spacer(Modifier.height(8.dp))
        OutlinedTextField(
            state.password,
            onPassword,
            label = { Text("Пароль") },
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        Spacer(Modifier.height(16.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = { onLogin(false) }, enabled = !state.isLoading) { Text("Войти") }
            OutlinedButton(onClick = { onLogin(true) }, enabled = !state.isLoading) { Text("Регистрация") }
        }
        state.message?.let {
            Spacer(Modifier.height(12.dp))
            Text(it, color = MaterialTheme.colorScheme.error)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ShoppingScreen(
    state: ShoppingUiState,
    onSync: () -> Unit,
    onSelectList: (Int) -> Unit,
    onCreateList: (String) -> Unit,
    onCreateItem: (String, String) -> Unit,
    onToggleItem: (Int, Boolean) -> Unit,
    onDeleteItem: (Int) -> Unit,
    onShareList: (String) -> Unit,
    onLoadMembers: () -> Unit,
    onLoadActivity: () -> Unit,
    onClearActivity: () -> Unit,
    onRenameList: (String) -> Unit,
    onCopyList: () -> Unit,
    onDeleteList: () -> Unit,
    onClearList: () -> Unit,
    onClearPurchased: () -> Unit,
    onRestorePurchased: () -> Unit,
    onUpdateItem: (Int, String, String) -> Unit,
    onUndoDeleteItem: () -> Unit,
    onCreateInviteLink: () -> Unit,
    onClearInviteUrl: () -> Unit,
    onAddCatalogProduct: (String) -> Unit,
    onRemoveCatalogProduct: (String) -> Unit,
    onSaveServerUrl: (String) -> Unit,
    onSaveThemeMode: (String) -> Unit,
    onLogout: () -> Unit
) {
    var itemName by remember { mutableStateOf("") }
    var quantity by remember { mutableStateOf("") }
    var menuOpen by remember { mutableStateOf(false) }
    var listMenuOpen by remember { mutableStateOf(false) }
    var createListDialogOpen by remember { mutableStateOf(false) }
    var selectListDialogOpen by remember { mutableStateOf(false) }
    var shareDialogOpen by remember { mutableStateOf(false) }
    var membersDialogOpen by remember { mutableStateOf(false) }
    var activityDialogOpen by remember { mutableStateOf(false) }
    var clearActivityDialogOpen by remember { mutableStateOf(false) }
    var renameDialogOpen by remember { mutableStateOf(false) }
    var deleteDialogOpen by remember { mutableStateOf(false) }
    var clearDialogOpen by remember { mutableStateOf(false) }
    var clearPurchasedDialogOpen by remember { mutableStateOf(false) }
    var inviteDialogOpen by remember { mutableStateOf(false) }
    var catalogDialogOpen by remember { mutableStateOf(false) }
    var settingsDialogOpen by remember { mutableStateOf(false) }
    var aboutDialogOpen by remember { mutableStateOf(false) }
    var editingItem by remember { mutableStateOf<com.shoppinglist.mobile.data.ShoppingItemDto?>(null) }
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val updateRepository = remember { UpdateRepository(context.applicationContext) }
    var appUpdateInfo by remember { mutableStateOf<AppUpdateInfo?>(null) }
    val selectedList = state.lists.firstOrNull { it.id == state.selectedListId }
    val visibleItems = remember(selectedList?.items) {
        selectedList?.items.orEmpty().sortedWith { first, second ->
            when {
                first.is_checked != second.is_checked -> if (first.is_checked) 1 else -1
                first.is_checked -> first.updated_at.compareTo(second.updated_at)
                else -> second.updated_at.compareTo(first.updated_at)
            }
        }
    }
    val activeItems = remember(visibleItems) { visibleItems.filterNot { it.is_checked } }
    val purchasedItems = remember(visibleItems) { visibleItems.filter { it.is_checked } }

    LaunchedEffect(Unit) {
        appUpdateInfo = updateRepository.checkForUpdate()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Покупки")
                        selectedList?.let {
                            Text(it.name, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                },
                navigationIcon = {
                    Icon(Icons.Default.ShoppingCart, contentDescription = null, modifier = Modifier.padding(start = 16.dp))
                },
                actions = {
                    IconButton(onClick = { createListDialogOpen = true }) {
                        Icon(Icons.Default.Add, contentDescription = "Создать список")
                    }
                    IconButton(onClick = onSync, enabled = !state.isLoading) {
                        Icon(Icons.Default.Refresh, contentDescription = "Обновить")
                    }
                    IconButton(onClick = { listMenuOpen = true }, enabled = selectedList != null) {
                        Icon(Icons.Default.Settings, contentDescription = "Меню списка")
                    }
                    ListDropdownMenu(
                        expanded = listMenuOpen,
                        onDismiss = { listMenuOpen = false },
                        enabled = selectedList != null,
                        onMembers = {
                            listMenuOpen = false
                            onLoadMembers()
                            membersDialogOpen = true
                        },
                        onActivity = {
                            listMenuOpen = false
                            onLoadActivity()
                            activityDialogOpen = true
                        },
                        onClearActivity = {
                            listMenuOpen = false
                            clearActivityDialogOpen = true
                        },
                        onRename = {
                            listMenuOpen = false
                            renameDialogOpen = true
                        },
                        onCopy = {
                            listMenuOpen = false
                            onCopyList()
                        },
                        onClear = {
                            listMenuOpen = false
                            clearDialogOpen = true
                        },
                        onClearPurchased = {
                            listMenuOpen = false
                            clearPurchasedDialogOpen = true
                        },
                        onRestorePurchased = {
                            listMenuOpen = false
                            onRestorePurchased()
                        },
                        onDelete = {
                            listMenuOpen = false
                            deleteDialogOpen = true
                        },
                        onShareByEmail = {
                            listMenuOpen = false
                            shareDialogOpen = true
                        },
                        onInvite = {
                            listMenuOpen = false
                            onCreateInviteLink()
                            inviteDialogOpen = true
                        }
                    )
                    IconButton(onClick = { menuOpen = true }) {
                        Icon(Icons.Default.MoreVert, contentDescription = "Меню")
                    }
                    DropdownMenu(expanded = menuOpen, onDismissRequest = { menuOpen = false }) {
                        DropdownMenuItem(
                            text = { Text("Выбрать список") },
                            leadingIcon = { Icon(Icons.Default.ShoppingCart, contentDescription = null) },
                            enabled = state.lists.isNotEmpty(),
                            onClick = {
                                menuOpen = false
                                selectListDialogOpen = true
                            }
                        )
                        DropdownMenuItem(
                            text = { Text("Справочник товаров") },
                            leadingIcon = { Icon(Icons.Default.Storefront, contentDescription = null) },
                            onClick = {
                                menuOpen = false
                                catalogDialogOpen = true
                            }
                        )
                        DropdownMenuItem(
                            text = { Text("Настройки") },
                            leadingIcon = { Icon(Icons.Default.Settings, contentDescription = null) },
                            onClick = {
                                menuOpen = false
                                settingsDialogOpen = true
                            }
                        )
                        DropdownMenuItem(
                            text = { Text("О приложении") },
                            leadingIcon = { Icon(Icons.Default.Info, contentDescription = null) },
                            onClick = {
                                menuOpen = false
                                aboutDialogOpen = true
                            }
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
            )
        }
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            appUpdateInfo?.let { updateInfo ->
                item {
                    UpdateBanner(
                        updateInfo = updateInfo,
                        onDownload = {
                            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(updateInfo.releaseUrl)))
                        },
                        onDismiss = {
                            scope.launch {
                                updateRepository.dismissUpdate(updateInfo.latestVersion)
                                appUpdateInfo = null
                            }
                        }
                    )
                }
            }

            if (selectedList != null) {
                item {
                    ItemCreateCard(
                        itemName = itemName,
                        quantity = quantity,
                        catalog = state.productCatalog,
                        onItemName = { itemName = it },
                        onQuantity = { quantity = it },
                        onPickSuggestion = { itemName = it },
                        onAdd = {
                            if (itemName.isNotBlank()) {
                                onCreateItem(itemName.trim(), quantity.trim())
                                itemName = ""
                                quantity = ""
                            }
                        }
                    )
                }

                if (state.canUndoDelete) {
                    item {
                        DeletedItemUndoCard(onUndo = onUndoDeleteItem)
                    }
                }

                if (activeItems.isNotEmpty()) {
                    item { ListSectionHeader("Купить") }
                    items(activeItems) { item ->
                        ShoppingItemRow(
                            item = item,
                            onToggleItem = onToggleItem,
                            onDeleteItem = onDeleteItem,
                            onEditItem = { editingItem = it }
                        )
                    }
                }

                if (purchasedItems.isNotEmpty()) {
                    item { ListSectionHeader("Куплено") }
                    items(purchasedItems) { item ->
                        ShoppingItemRow(
                            item = item,
                            onToggleItem = onToggleItem,
                            onDeleteItem = onDeleteItem,
                            onEditItem = { editingItem = it }
                        )
                    }
                }

                if (state.isOffline || state.pendingOperationCount > 0 || state.lastSuccessfulSync != null) {
                    item {
                        SyncStatusCard(
                            isOffline = state.isOffline,
                            pendingOperationCount = state.pendingOperationCount,
                            lastSuccessfulSync = state.lastSuccessfulSync,
                            onSync = onSync
                        )
                    }
                }
            } else {
                item {
                    ElevatedCard {
                        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("Создайте первый список", style = MaterialTheme.typography.titleMedium)
                            Text("Нажмите + в верхней панели, чтобы добавить список.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }

            state.message?.let {
                item {
                    Text(it, color = MaterialTheme.colorScheme.primary)
                }
            }
        }
    }

    if (createListDialogOpen) {
        CreateListDialog(
            onDismiss = { createListDialogOpen = false },
            onCreate = {
                onCreateList(it)
                createListDialogOpen = false
            }
        )
    }

    if (selectListDialogOpen) {
        SelectListDialog(
            lists = state.lists,
            selectedListId = state.selectedListId,
            onDismiss = { selectListDialogOpen = false },
            onSelect = {
                onSelectList(it)
                selectListDialogOpen = false
            }
        )
    }

    if (shareDialogOpen && selectedList != null) {
        ShareDialog(
            onDismiss = { shareDialogOpen = false },
            onShare = {
                onShareList(it)
                shareDialogOpen = false
            }
        )
    }

    if (membersDialogOpen) {
        MembersDialog(
            members = state.selectedMembers,
            onDismiss = { membersDialogOpen = false }
        )
    }

    if (activityDialogOpen) {
        ActivityDialog(
            events = state.selectedActivity,
            onDismiss = { activityDialogOpen = false }
        )
    }

    if (renameDialogOpen && selectedList != null) {
        RenameListDialog(
            currentName = selectedList.name,
            onDismiss = { renameDialogOpen = false },
            onSave = {
                onRenameList(it)
                renameDialogOpen = false
            }
        )
    }

    if (deleteDialogOpen && selectedList != null) {
        ConfirmDeleteDialog(
            listName = selectedList.name,
            onDismiss = { deleteDialogOpen = false },
            onDelete = {
                onDeleteList()
                deleteDialogOpen = false
            }
        )
    }

    if (clearDialogOpen && selectedList != null) {
        ConfirmClearDialog(
            listName = selectedList.name,
            onDismiss = { clearDialogOpen = false },
            onClear = {
                onClearList()
                clearDialogOpen = false
            }
        )
    }

    if (clearPurchasedDialogOpen && selectedList != null) {
        ConfirmClearPurchasedDialog(
            listName = selectedList.name,
            onDismiss = { clearPurchasedDialogOpen = false },
            onClear = {
                onClearPurchased()
                clearPurchasedDialogOpen = false
            }
        )
    }

    if (clearActivityDialogOpen && selectedList != null) {
        ConfirmClearActivityDialog(
            listName = selectedList.name,
            onDismiss = { clearActivityDialogOpen = false },
            onClear = {
                onClearActivity()
                clearActivityDialogOpen = false
            }
        )
    }

    editingItem?.let { item ->
        EditItemDialog(
            itemName = item.name,
            quantity = item.quantity,
            onDismiss = { editingItem = null },
            onSave = { name, nextQuantity ->
                onUpdateItem(item.id, name, nextQuantity)
                editingItem = null
            }
        )
    }

    if (inviteDialogOpen) {
        InviteLinkDialog(
            inviteUrl = state.inviteUrl,
            onDismiss = {
                inviteDialogOpen = false
                onClearInviteUrl()
            }
        )
    }

    if (settingsDialogOpen) {
        SettingsDialog(
            serverUrl = state.serverUrl,
            themeMode = state.themeMode,
            onDismiss = { settingsDialogOpen = false },
            onSaveServerUrl = {
                onSaveServerUrl(it)
                settingsDialogOpen = false
            },
            onSaveThemeMode = onSaveThemeMode,
            onLogout = {
                onLogout()
                settingsDialogOpen = false
            }
        )
    }

    if (aboutDialogOpen) {
        AboutDialog(updateRepository = updateRepository, onDismiss = { aboutDialogOpen = false })
    }

    if (catalogDialogOpen) {
        CatalogDialog(
            catalog = state.productCatalog,
            onDismiss = { catalogDialogOpen = false },
            onAdd = onAddCatalogProduct,
            onRemove = onRemoveCatalogProduct
        )
    }
}

@Composable
private fun UpdateBanner(
    updateInfo: AppUpdateInfo,
    onDownload: () -> Unit,
    onDismiss: () -> Unit
) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp)
        ) {
            Icon(Icons.Default.Info, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimaryContainer)
            Text(
                text = "Доступна новая версия приложения: ${updateInfo.latestVersion}",
                color = MaterialTheme.colorScheme.onPrimaryContainer,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.weight(1f)
            )
            TextButton(onClick = onDownload) {
                Text("Скачать")
            }
            TextButton(onClick = onDismiss) {
                Text("Скрыть")
            }
        }
    }
}

@Composable
private fun ListSectionHeader(title: String) {
    Text(
        text = title,
        style = MaterialTheme.typography.labelLarge,
        color = MaterialTheme.colorScheme.primary,
        modifier = Modifier.padding(start = 4.dp, top = 8.dp, bottom = 2.dp)
    )
}

@Composable
private fun DeletedItemUndoCard(onUndo: () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp)
        ) {
            Text(
                "Товар удалён",
                color = MaterialTheme.colorScheme.onSecondaryContainer,
                modifier = Modifier.weight(1f)
            )
            TextButton(onClick = onUndo) {
                Icon(Icons.Default.Undo, contentDescription = null)
                Text("Отменить", modifier = Modifier.padding(start = 6.dp))
            }
        }
    }
}

@Composable
private fun SyncStatusCard(
    isOffline: Boolean,
    pendingOperationCount: Int,
    lastSuccessfulSync: String?,
    onSync: () -> Unit
) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp)
        ) {
            Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    if (isOffline) "Сервер недоступен" else "Синхронизация активна",
                    style = MaterialTheme.typography.labelLarge,
                    color = if (isOffline) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary
                )
                if (pendingOperationCount > 0) {
                    Text(
                        "Ожидает отправки: $pendingOperationCount",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                lastSuccessfulSync?.let {
                    Text(
                        "Последняя синхронизация: ${formatDateTime(it)}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            IconButton(onClick = onSync, modifier = Modifier.size(40.dp)) {
                Icon(Icons.Default.Refresh, contentDescription = "Повторить синхронизацию")
            }
        }
    }
}

@Composable
private fun ShoppingItemRow(
    item: com.shoppinglist.mobile.data.ShoppingItemDto,
    onToggleItem: (Int, Boolean) -> Unit,
    onDeleteItem: (Int) -> Unit,
    onEditItem: (com.shoppinglist.mobile.data.ShoppingItemDto) -> Unit
) {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 0.dp)
        ) {
            Checkbox(
                checked = item.is_checked,
                onCheckedChange = { checked -> onToggleItem(item.id, checked) },
                modifier = Modifier.size(40.dp)
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = item.name,
                    style = MaterialTheme.typography.titleSmall,
                    textDecoration = if (item.is_checked) TextDecoration.LineThrough else TextDecoration.None,
                    modifier = Modifier.clickable { onEditItem(item) }
                )
                if (item.quantity.isNotBlank()) {
                    Text(
                        item.quantity,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.clickable { onEditItem(item) }
                    )
                }
            }
            IconButton(onClick = { onDeleteItem(item.id) }, modifier = Modifier.size(40.dp)) {
                Icon(Icons.Default.Delete, contentDescription = "Удалить товар")
            }
        }
    }
}

@Composable
private fun ItemCreateCard(
    itemName: String,
    quantity: String,
    catalog: List<String>,
    onItemName: (String) -> Unit,
    onQuantity: (String) -> Unit,
    onPickSuggestion: (String) -> Unit,
    onAdd: () -> Unit
) {
    val suggestions = remember(itemName, catalog) {
        val query = itemName.trim()
        if (query.length < 2) {
            emptyList()
        } else {
            catalog
                .filter { it.contains(query, ignoreCase = true) && !it.equals(query, ignoreCase = true) }
                .take(5)
        }
    }

    ElevatedCard {
        Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    itemName,
                    onItemName,
                    placeholder = { Text("Товар") },
                    modifier = Modifier
                        .weight(1f)
                        .height(56.dp),
                    singleLine = true
                )
                OutlinedTextField(
                    quantity,
                    onQuantity,
                    placeholder = { Text("Кол-во") },
                    modifier = Modifier
                        .weight(0.65f)
                        .height(56.dp),
                    singleLine = true
                )
                IconButton(onClick = onAdd, modifier = Modifier.size(40.dp)) {
                    Icon(Icons.Default.Add, contentDescription = "Добавить товар")
                }
            }
            if (suggestions.isNotEmpty()) {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Подсказки", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                        items(suggestions) { suggestion ->
                            AssistChip(onClick = { onPickSuggestion(suggestion) }, label = { Text(suggestion) })
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ListDropdownMenu(
    expanded: Boolean,
    enabled: Boolean,
    onDismiss: () -> Unit,
    onMembers: () -> Unit,
    onActivity: () -> Unit,
    onClearActivity: () -> Unit,
    onRename: () -> Unit,
    onCopy: () -> Unit,
    onClear: () -> Unit,
    onClearPurchased: () -> Unit,
    onRestorePurchased: () -> Unit,
    onDelete: () -> Unit,
    onShareByEmail: () -> Unit,
    onInvite: () -> Unit
) {
    DropdownMenu(expanded = expanded, onDismissRequest = onDismiss) {
        DropdownMenuItem(
            text = { Text("Участники") },
            leadingIcon = { Icon(Icons.Default.People, contentDescription = null) },
            enabled = enabled,
            onClick = onMembers
        )
        DropdownMenuItem(
            text = { Text("История") },
            leadingIcon = { Icon(Icons.Default.History, contentDescription = null) },
            enabled = enabled,
            onClick = onActivity
        )
        DropdownMenuItem(
            text = { Text("Очистить историю") },
            leadingIcon = { Icon(Icons.Default.History, contentDescription = null) },
            enabled = enabled,
            onClick = onClearActivity
        )
        DropdownMenuItem(
            text = { Text("Переименовать") },
            leadingIcon = { Icon(Icons.Default.Edit, contentDescription = null) },
            enabled = enabled,
            onClick = onRename
        )
        DropdownMenuItem(
            text = { Text("Скопировать") },
            leadingIcon = { Icon(Icons.Default.ContentCopy, contentDescription = null) },
            enabled = enabled,
            onClick = onCopy
        )
        DropdownMenuItem(
            text = { Text("Очистить") },
            leadingIcon = { Icon(Icons.Default.CleaningServices, contentDescription = null) },
            enabled = enabled,
            onClick = onClear
        )
        DropdownMenuItem(
            text = { Text("Очистить купленные") },
            leadingIcon = { Icon(Icons.Default.CheckCircle, contentDescription = null) },
            enabled = enabled,
            onClick = onClearPurchased
        )
        DropdownMenuItem(
            text = { Text("Вернуть купленные") },
            leadingIcon = { Icon(Icons.Default.Undo, contentDescription = null) },
            enabled = enabled,
            onClick = onRestorePurchased
        )
        DropdownMenuItem(
            text = { Text("Удалить") },
            leadingIcon = { Icon(Icons.Default.Delete, contentDescription = null) },
            enabled = enabled,
            onClick = onDelete
        )
        DropdownMenuItem(
            text = { Text("Открыть по email") },
            leadingIcon = { Icon(Icons.Default.Share, contentDescription = null) },
            enabled = enabled,
            onClick = onShareByEmail
        )
        DropdownMenuItem(
            text = { Text("Ссылка-приглашение") },
            leadingIcon = { Icon(Icons.Default.Link, contentDescription = null) },
            enabled = enabled,
            onClick = onInvite
        )
    }
}

@Composable
private fun CreateListDialog(onDismiss: () -> Unit, onCreate: (String) -> Unit) {
    var name by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Новый список") },
        text = {
            OutlinedTextField(
                name,
                { name = it },
                label = { Text("Название списка") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
        },
        confirmButton = {
            Button(onClick = { if (name.isNotBlank()) onCreate(name.trim()) }) {
                Text("Создать")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Отмена") }
        }
    )
}

@Composable
private fun SelectListDialog(
    lists: List<com.shoppinglist.mobile.data.ShoppingListDto>,
    selectedListId: Int?,
    onDismiss: () -> Unit,
    onSelect: (Int) -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Выбрать список") },
        text = {
            LazyColumn(modifier = Modifier.height(320.dp)) {
                items(lists) { list ->
                    FilterChip(
                        selected = list.id == selectedListId,
                        onClick = { onSelect(list.id) },
                        label = { Text(list.name) },
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp)
                    )
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) { Text("Закрыть") }
        }
    )
}

@Composable
private fun ShareDialog(onDismiss: () -> Unit, onShare: (String) -> Unit) {
    var email by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Открыть доступ") },
        text = {
            OutlinedTextField(
                email,
                { email = it },
                label = { Text("Email пользователя") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
        },
        confirmButton = {
            Button(onClick = { if (email.isNotBlank()) onShare(email.trim()) }) {
                Text("Открыть")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Отмена") }
        }
    )
}

@Composable
private fun MembersDialog(members: List<com.shoppinglist.mobile.data.ListMemberDto>, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Участники списка") },
        text = {
            if (members.isEmpty()) {
                Text("Загрузка участников...")
            } else {
                LazyColumn(modifier = Modifier.height(260.dp)) {
                    items(members) { member ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(member.email, style = MaterialTheme.typography.bodyLarge)
                                if (member.is_owner) {
                                    Text("Владелец", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
                                }
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(onClick = onDismiss) { Text("Закрыть") }
        }
    )
}

@Composable
private fun ActivityDialog(events: List<com.shoppinglist.mobile.data.ActivityLogDto>, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("История списка") },
        text = {
            if (events.isEmpty()) {
                Text("История пока пуста или загружается...")
            } else {
                LazyColumn(modifier = Modifier.height(360.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(events) { event ->
                        Column {
                            Text(activityTitle(event), style = MaterialTheme.typography.bodyLarge)
                            Text(
                                listOfNotNull(event.user_email, formatDateTime(event.created_at)).joinToString(" · "),
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            if (event.details.isNotBlank()) {
                                Text(
                                    event.details,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            HorizontalDivider(modifier = Modifier.padding(top = 8.dp))
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(onClick = onDismiss) { Text("Закрыть") }
        }
    )
}

private fun activityTitle(event: com.shoppinglist.mobile.data.ActivityLogDto): String {
    val itemName = event.item_name.ifBlank { "товар" }
    return when (event.action) {
        "list_created" -> "Создан список"
        "list_renamed" -> "Список переименован"
        "list_deleted" -> "Список удалён"
        "list_left" -> "Пользователь вышел из списка"
        "list_cleared" -> "Список очищен"
        "checked_items_cleared" -> "Купленные товары очищены"
        "checked_items_restored" -> "Купленные товары возвращены"
        "list_copied" -> "Список скопирован"
        "list_shared" -> "Открыт доступ к списку"
        "invite_created" -> "Создана ссылка-приглашение"
        "invite_accepted" -> "Принято приглашение"
        "item_created" -> "Добавлен товар: $itemName"
        "item_updated" -> "Изменён товар: $itemName"
        "item_checked" -> "Куплено: $itemName"
        "item_unchecked" -> "Возвращено к покупке: $itemName"
        "item_deleted" -> "Удалён товар: $itemName"
        else -> event.action
    }
}

private fun formatDateTime(value: String): String {
    return runCatching {
        val instant = java.time.Instant.parse(value)
        val formatter = java.time.format.DateTimeFormatter.ofPattern("dd.MM.yyyy HH:mm")
            .withZone(java.time.ZoneId.systemDefault())
        formatter.format(instant)
    }.getOrDefault(value)
}

@Composable
private fun RenameListDialog(currentName: String, onDismiss: () -> Unit, onSave: (String) -> Unit) {
    var name by remember(currentName) { mutableStateOf(currentName) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Переименовать список") },
        text = {
            OutlinedTextField(
                name,
                { name = it },
                label = { Text("Название списка") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
        },
        confirmButton = {
            Button(onClick = { if (name.isNotBlank()) onSave(name.trim()) }) {
                Text("Сохранить")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Отмена") }
        }
    )
}

@Composable
private fun ConfirmDeleteDialog(listName: String, onDismiss: () -> Unit, onDelete: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Удалить список?") },
        text = { Text("Если вы владелец, список будет удален для всех. Если нет, список будет скрыт только у вас.") },
        confirmButton = {
            Button(onClick = onDelete) { Text("Удалить") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Отмена") }
        }
    )
}

@Composable
private fun ConfirmClearDialog(listName: String, onDismiss: () -> Unit, onClear: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Очистить список?") },
        text = { Text("Все позиции из списка «$listName» будут удалены.") },
        confirmButton = {
            Button(onClick = onClear) { Text("Очистить") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Отмена") }
        }
    )
}

@Composable
private fun ConfirmClearPurchasedDialog(listName: String, onDismiss: () -> Unit, onClear: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Очистить купленные?") },
        text = { Text("Все отмеченные как купленные позиции из списка «$listName» будут удалены.") },
        confirmButton = {
            Button(onClick = onClear) { Text("Очистить") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Отмена") }
        }
    )
}

@Composable
private fun ConfirmClearActivityDialog(listName: String, onDismiss: () -> Unit, onClear: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Очистить историю?") },
        text = { Text("История действий списка «$listName» будет удалена. Сами товары и список останутся без изменений.") },
        confirmButton = {
            Button(onClick = onClear) { Text("Очистить") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Отмена") }
        }
    )
}

@Composable
private fun EditItemDialog(
    itemName: String,
    quantity: String,
    onDismiss: () -> Unit,
    onSave: (String, String) -> Unit
) {
    var name by remember(itemName) { mutableStateOf(itemName) }
    var nextQuantity by remember(quantity) { mutableStateOf(quantity) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Редактировать товар") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    name,
                    { name = it },
                    label = { Text("Товар") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
                OutlinedTextField(
                    nextQuantity,
                    { nextQuantity = it },
                    label = { Text("Количество") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
            }
        },
        confirmButton = {
            Button(onClick = { if (name.isNotBlank()) onSave(name.trim(), nextQuantity.trim()) }) {
                Text("Сохранить")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Отмена") }
        }
    )
}

@Composable
private fun InviteLinkDialog(inviteUrl: String, onDismiss: () -> Unit) {
    val context = LocalContext.current
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Ссылка-приглашение") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Отправьте ссылку пользователю. После входа в приложение он автоматически присоединится к списку.")
                if (inviteUrl.isBlank()) {
                    Text("Создание ссылки...")
                } else {
                    OutlinedTextField(
                        inviteUrl,
                        {},
                        label = { Text("Ссылка") },
                        modifier = Modifier.fillMaxWidth(),
                        readOnly = true
                    )
                    OutlinedButton(
                        onClick = {
                            val sendIntent = Intent(Intent.ACTION_SEND).apply {
                                type = "text/plain"
                                putExtra(Intent.EXTRA_TEXT, inviteUrl)
                            }
                            context.startActivity(Intent.createChooser(sendIntent, "Отправить ссылку"))
                        }
                    ) {
                        Text("Отправить...")
                    }
                }
            }
        },
        confirmButton = {
            Button(
                enabled = inviteUrl.isNotBlank(),
                onClick = {
                    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                    clipboard.setPrimaryClip(ClipData.newPlainText("Ссылка на список покупок", inviteUrl))
                    onDismiss()
                }
            ) {
                Text("Скопировать")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Закрыть") }
        }
    )
}

@Composable
private fun SettingsDialog(
    serverUrl: String,
    themeMode: String,
    onDismiss: () -> Unit,
    onSaveServerUrl: (String) -> Unit,
    onSaveThemeMode: (String) -> Unit,
    onLogout: () -> Unit
) {
    var nextServerUrl by remember(serverUrl) { mutableStateOf(serverUrl) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Настройки") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(
                    nextServerUrl,
                    { nextServerUrl = it },
                    label = { Text("Адрес сервера") },
                    placeholder = { Text("https://shopping.example.com") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
                Text("Тема", style = MaterialTheme.typography.titleSmall)
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    item {
                        FilterChip(
                            selected = themeMode == "system",
                            onClick = { onSaveThemeMode("system") },
                            label = { Text("Как в системе") }
                        )
                    }
                    item {
                        FilterChip(
                            selected = themeMode == "light",
                            onClick = { onSaveThemeMode("light") },
                            label = { Text("Светлая") }
                        )
                    }
                    item {
                        FilterChip(
                            selected = themeMode == "dark",
                            onClick = { onSaveThemeMode("dark") },
                            label = { Text("Тёмная") }
                        )
                    }
                }
                HorizontalDivider()
                OutlinedButton(onClick = onLogout, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Default.Logout, contentDescription = null)
                    Text("Выйти из аккаунта", modifier = Modifier.padding(start = 8.dp))
                }
            }
        },
        confirmButton = {
            Button(onClick = { onSaveServerUrl(nextServerUrl) }) {
                Text("Сохранить")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Закрыть") }
        }
    )
}

@Composable
private fun AboutDialog(updateRepository: UpdateRepository, onDismiss: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val projectUrl = "https://github.com/shurshick/shopping-list"
    var updateStatus by remember { mutableStateOf("") }
    var updateUrl by remember { mutableStateOf<String?>(null) }
    var isCheckingUpdate by remember { mutableStateOf(false) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("О приложении") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Список покупок", style = MaterialTheme.typography.titleMedium)
                Text("Версия ${BuildConfig.VERSION_NAME}")
                Text("© 2026 shurshick")
                OutlinedTextField(
                    projectUrl,
                    {},
                    label = { Text("Проект") },
                    modifier = Modifier.fillMaxWidth(),
                    readOnly = true
                )
                OutlinedButton(
                    onClick = {
                        scope.launch {
                            isCheckingUpdate = true
                            updateStatus = "Проверяем обновление..."
                            updateUrl = null
                            val result = updateRepository.checkForUpdate(force = true)
                            isCheckingUpdate = false
                            if (result == null) {
                                updateStatus = ""
                            } else {
                                updateStatus = "Доступна новая версия ${result.latestVersion}."
                                updateUrl = result.releaseUrl
                            }
                        }
                    },
                    enabled = !isCheckingUpdate,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(if (isCheckingUpdate) "Проверка..." else "Проверить обновление")
                }
                if (updateStatus.isNotBlank()) {
                    Text(updateStatus, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                updateUrl?.let { apkUrl ->
                    Button(
                        onClick = {
                            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(apkUrl)))
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Скачать обновление")
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(projectUrl)))
                }
            ) {
                Text("Открыть проект")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Закрыть") }
        }
    )
}

@Composable
private fun CatalogDialog(
    catalog: List<String>,
    onDismiss: () -> Unit,
    onAdd: (String) -> Unit,
    onRemove: (String) -> Unit
) {
    var productName by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Справочник товаров") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    OutlinedTextField(
                        productName,
                        { productName = it },
                        label = { Text("Название товара") },
                        modifier = Modifier.weight(1f),
                        singleLine = true
                    )
                    IconButton(onClick = {
                        if (productName.isNotBlank()) {
                            onAdd(productName)
                            productName = ""
                        }
                    }) {
                        Icon(Icons.Default.Add, contentDescription = "Добавить в справочник")
                    }
                }
                HorizontalDivider()
                LazyColumn(modifier = Modifier.height(320.dp)) {
                    items(catalog) { product ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(product, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodyLarge)
                            IconButton(onClick = { onRemove(product) }) {
                                Icon(Icons.Default.Delete, contentDescription = "Удалить")
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(onClick = onDismiss) { Text("Готово") }
        }
    )
}
