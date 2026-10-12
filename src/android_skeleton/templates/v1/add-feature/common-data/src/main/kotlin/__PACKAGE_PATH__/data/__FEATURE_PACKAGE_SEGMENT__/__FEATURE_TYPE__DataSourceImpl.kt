package __PACKAGE__.data.__FEATURE_PACKAGE_SEGMENT__

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import __PACKAGE__.domain.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__Model
import kotlinx.coroutines.flow.first
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

/**
 * Offline-first source of __FEATURE_SLUG__ data.
 *
 * `__FEATURE_SLUG___stub.json` is a local stand-in for a backend response until the real endpoint is
 * available. It ships with the feature module, and Android merges the assets of every library into
 * the application, so reading it by name from here resolves to that file.
 *
 * The parser intentionally accepts any valid JSON shape and uses a meaningful `id` when present;
 * otherwise it keeps the complete JSON as the model identifier so the response is never discarded.
 */
class __FEATURE_TYPE__DataSourceImpl(
    private val dataStore: DataStore<Preferences>,
    private val context: Context,
) : __FEATURE_TYPE__DataSource {
    private val json = Json { ignoreUnknownKeys = true }

    override suspend fun loadLocal(): __FEATURE_TYPE__Model? =
        dataStore.data.first()[MODEL_ID]?.let(::__FEATURE_TYPE__Model)

    override suspend fun loadRemote(): __FEATURE_TYPE__Model {
        val response = context.assets.open(STUB_ASSET).bufferedReader().use { it.readText() }
        return __FEATURE_TYPE__Model(id = extractId(json.parseToJsonElement(response)))
    }

    override suspend fun saveLocal(model: __FEATURE_TYPE__Model) {
        dataStore.edit { preferences -> preferences[MODEL_ID] = model.id }
    }

    private fun extractId(element: JsonElement): String = when (element) {
        is JsonObject -> {
            val directId = element["id"]?.asText()
                ?: element["data"]?.let(::extractIdOrNull)
                ?: element["result"]?.let(::extractIdOrNull)
            directId ?: element.values.asSequence().mapNotNull(::extractIdOrNull).firstOrNull()
                ?: element.toString()
        }
        is JsonArray -> element.asSequence().mapNotNull(::extractIdOrNull).firstOrNull()
            ?: element.toString()
        else -> element.asText() ?: element.toString()
    }

    private fun extractIdOrNull(element: JsonElement): String? = runCatching {
        extractId(element)
    }.getOrNull()

    private fun JsonElement.asText(): String? = (this as? JsonPrimitive)
        ?.takeIf { it.isString || it.content != "null" }
        ?.content

    private companion object {
        val MODEL_ID = stringPreferencesKey("__FEATURE_SLUG___id")
        const val STUB_ASSET = "__FEATURE_SLUG___stub.json"
    }
}