package __PACKAGE__.feature.__FEATURE_PACKAGE_SEGMENT__.di

import __PACKAGE__.data.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__DataSource
import __PACKAGE__.data.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__DataSourceImpl
import __PACKAGE__.data.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__RepositoryImpl
import __PACKAGE__.domain.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__Repository
import __PACKAGE__.domain.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__UseCase
import __PACKAGE__.feature.__FEATURE_PACKAGE_SEGMENT__.presentation.__FEATURE_TYPE__ViewModel
import org.koin.android.ext.koin.androidContext
import org.koin.core.module.dsl.viewModel
import org.koin.dsl.module

/**
 * DI registrations of the whole __FEATURE_SLUG__ chain: data source, repository, use case and
 * ViewModel. Registering the use case rather than the repository in the ViewModel keeps the layer
 * boundary enforced by the constructor.
 *
 * The implementations live in the shared domain and data modules; this module binds them for this
 * feature, because only the feature knows which types belong to it.
 */
val __FEATURE_LOWER_CAMEL__Module = module {
    single<__FEATURE_TYPE__DataSource> { __FEATURE_TYPE__DataSourceImpl(get(), androidContext()) }
    single<__FEATURE_TYPE__Repository> { __FEATURE_TYPE__RepositoryImpl(get()) }
    single { __FEATURE_TYPE__UseCase(get()) }
    viewModel { __FEATURE_TYPE__ViewModel(get()) }
}