package __PACKAGE__.core.datastore

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.preferencesDataStore
import org.koin.android.ext.koin.androidContext
import org.koin.dsl.module

private val Context.appPreferences by preferencesDataStore(name = "app_preferences")

val coreDataStoreModule = module {
    single<DataStore<Preferences>> {
        androidContext().appPreferences
    }
}
