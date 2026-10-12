package __PACKAGE__.data.__FEATURE_PACKAGE_SEGMENT__

import __PACKAGE__.domain.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__Model
import __PACKAGE__.domain.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__Repository

class __FEATURE_TYPE__RepositoryImpl(
    private val dataSource: __FEATURE_TYPE__DataSource,
) : __FEATURE_TYPE__Repository {
    override suspend fun load(): __FEATURE_TYPE__Model? {
        return runCatching {
            dataSource.loadRemote().also { dataSource.saveLocal(it) }
        }.getOrElse {
            dataSource.loadLocal() ?: throw it
        }
    }
}