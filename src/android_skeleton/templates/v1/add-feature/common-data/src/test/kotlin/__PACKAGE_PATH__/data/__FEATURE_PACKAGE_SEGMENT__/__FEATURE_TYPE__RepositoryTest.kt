package __PACKAGE__.data.__FEATURE_PACKAGE_SEGMENT__

import __PACKAGE__.domain.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__Model
import __PACKAGE__.domain.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__Repository
import __PACKAGE__.domain.__FEATURE_PACKAGE_SEGMENT__.__FEATURE_TYPE__UseCase
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows

private class FakeDataSource(
    private val remote: () -> __FEATURE_TYPE__Model,
    private val local: () -> __FEATURE_TYPE__Model? = { null },
) : __FEATURE_TYPE__DataSource {
    var saved: __FEATURE_TYPE__Model? = null

    override suspend fun loadLocal(): __FEATURE_TYPE__Model? = local()
    override suspend fun loadRemote(): __FEATURE_TYPE__Model = remote()
    override suspend fun saveLocal(model: __FEATURE_TYPE__Model) { saved = model }
}

class __FEATURE_TYPE__RepositoryTest {
    @Test
    fun `repository returns remote data and caches it`() = runTest {
        val dataSource = FakeDataSource(remote = { __FEATURE_TYPE__Model(id = "42") })
        val repository = __FEATURE_TYPE__RepositoryImpl(dataSource)

        assertEquals(__FEATURE_TYPE__Model(id = "42"), repository.load())
        assertEquals(__FEATURE_TYPE__Model(id = "42"), dataSource.saved)
    }

    @Test
    fun `repository propagates an error when there is no cached data`() = runTest {
        val repository = __FEATURE_TYPE__RepositoryImpl(
            FakeDataSource(
                remote = { throw IllegalStateException("offline") },
                local = { null },
            ),
        )

        assertThrows<IllegalStateException> { repository.load() }
    }

    @Test
    fun `repository returns cached data when remote loading fails`() = runTest {
        val repository = __FEATURE_TYPE__RepositoryImpl(
            FakeDataSource(
                remote = { throw IllegalStateException("offline") },
                local = { __FEATURE_TYPE__Model(id = "cached") },
            ),
        )

        assertEquals(__FEATURE_TYPE__Model(id = "cached"), repository.load())
    }

    @Test
    fun `use case keeps the repository boundary`() = runTest {
        var calls = 0
        val repository = object : __FEATURE_TYPE__Repository {
            override suspend fun load(): __FEATURE_TYPE__Model? =
                __FEATURE_TYPE__Model(id = "${++calls}")
        }
        val useCase = __FEATURE_TYPE__UseCase(repository)

        assertEquals(__FEATURE_TYPE__Model(id = "1"), useCase())
        assertEquals(__FEATURE_TYPE__Model(id = "2"), useCase())
        assertEquals(2, calls)
    }
}