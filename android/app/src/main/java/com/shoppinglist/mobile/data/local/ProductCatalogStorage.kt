package com.shoppinglist.mobile.data.local

import android.content.Context
import java.util.Locale

class ProductCatalogStorage(context: Context) {
    private val preferences = context.getSharedPreferences("shopping-list", Context.MODE_PRIVATE)

    fun load(defaultProducts: List<String>): List<String> {
        val stored = preferences.getString("productCatalog", null)
        return stored
            ?.split("\n")
            ?.let(::normalizeCatalogProducts)
            ?: normalizeCatalogProducts(defaultProducts)
    }

    fun save(catalog: List<String>) {
        val cleanedCatalog = normalizeCatalogProducts(catalog)
        preferences.edit().putString("productCatalog", cleanedCatalog.joinToString("\n")).apply()
    }
}

internal fun normalizeCatalogProducts(catalog: List<String>): List<String> {
    val uniqueProducts = linkedMapOf<String, String>()
    catalog.forEach { product ->
        val normalizedName = product.trim()
        if (normalizedName.isNotBlank()) {
            uniqueProducts.putIfAbsent(normalizedName.lowercase(Locale.ROOT), normalizedName)
        }
    }
    return uniqueProducts.values.sortedWith(String.CASE_INSENSITIVE_ORDER)
}
