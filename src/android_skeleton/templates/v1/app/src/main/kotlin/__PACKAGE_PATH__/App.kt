package __PACKAGE__

import android.app.Application

import __PACKAGE__.core.datastore.coreDataStoreModule
import __PACKAGE__.feature.home.di.homeModule__OPTIONAL_KOIN_IMPORTS__
import org.koin.android.ext.koin.androidContext
import org.koin.core.context.startKoin
import org.koin.dsl.module

class App : Application() {
    override fun onCreate() {
        super.onCreate()
        startKoin {
            androidContext(this@App)
            modules(module {}, homeModule, coreDataStoreModule__OPTIONAL_KOIN_MODULES__)
        }
    }
}