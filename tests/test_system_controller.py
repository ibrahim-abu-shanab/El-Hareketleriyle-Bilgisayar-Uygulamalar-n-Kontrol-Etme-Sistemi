from jestkontrol.application.system_controller import SystemController
from jestkontrol.domain.modes import OperatingMode, SystemState

OFF, ACTIVE, PAUSED = SystemState.OFF, SystemState.ACTIVE, SystemState.PAUSED


def test_initial_state_is_off_in_mouse_mode():
    controller = SystemController()

    assert (controller.state, controller.mode) == (OFF, OperatingMode.MOUSE)


def test_full_lifecycle():
    controller = SystemController()

    controller.start()
    assert controller.state is ACTIVE
    controller.pause()
    assert controller.state is PAUSED
    controller.resume()
    assert controller.state is ACTIVE
    controller.stop()
    assert controller.state is OFF


def test_stop_works_from_paused():
    controller = SystemController()
    controller.start()
    controller.pause()

    controller.stop()

    assert controller.state is OFF


def test_invalid_transitions_are_ignored():
    controller = SystemController()

    controller.pause()
    controller.resume()
    controller.toggle_pause()

    assert controller.state is OFF


def test_toggle_pause_flips_between_active_and_paused():
    controller = SystemController()
    controller.start()

    controller.toggle_pause()
    assert controller.state is PAUSED
    controller.toggle_pause()
    assert controller.state is ACTIVE


def test_listeners_are_notified_only_on_real_changes():
    controller = SystemController()
    statuses = []
    controller.subscribe(statuses.append)

    controller.start()
    controller.start()  # no change
    controller.set_mode(OperatingMode.VOLUME)
    controller.set_mode(OperatingMode.VOLUME)  # no change

    assert [(s.state, s.mode) for s in statuses] == [
        (ACTIVE, OperatingMode.MOUSE),
        (ACTIVE, OperatingMode.VOLUME),
    ]
