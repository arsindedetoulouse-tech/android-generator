package __PACKAGE__.data.__FEATURE_PACKAGE_SEGMENT__

import __PACKAGE__.domain.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__Model

/**
 * Sources of __FEATURE_SLUG__ data, split by where the data comes from.
 *
 * The split is what makes the feature offline-first: the repository can show a cached model while the
 * remote source is unavailable, and can persist a freshly loaded one.
 */
interface __FEATURE_TYPE__DataSource {
    suspend fun loadLocal(): __FEATURE_TYPE__Model?

    suspend fun loadRemote(): __FEATURE_TYPE__Model

    suspend fun saveLocal(model: __FEATURE_TYPE__Model)
}