package __PACKAGE__.presentation

import androidx.lifecycle.ViewModel
import org.orbitmvi.orbit.OrbitContainerHost
import org.orbitmvi.orbit.viewmodel.orbitContainer

abstract class BaseViewModel<STATE : Any, SIDE_EFFECT : Any>(
    initialState: STATE,
) : ViewModel(), OrbitContainerHost<STATE, STATE, SIDE_EFFECT> {
    override val container = orbitContainer<STATE, SIDE_EFFECT>(initialState)
}
