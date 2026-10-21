from jestkontrol.application.frame_processor import FrameResult
from jestkontrol.application.hand_presence import NO_HAND_NOTICE_AFTER_S, HandPresenceMonitor
from jestkontrol.application.system_controller import SystemController
from tests.fakes import FakeClock
from tests.hands import open_hand

NO_HAND = FrameResult(None, ())
WITH_HAND = FrameResult(open_hand(), ())


def make_monitor(start=True):
    clock = FakeClock()
    controller = SystemController()
    if start:
        controller.start()
    monitor = HandPresenceMonitor(clock, controller)
    notices = []
    monitor.subscribe(lambda: notices.append(clock.now()))
    return monitor, clock, controller, notices


def feed(monitor, clock, result, seconds, step=0.1):
    for _ in range(round(seconds / step)):
        monitor.on_frame(object(), result)
        clock.advance(step)


def test_notifies_once_when_the_hand_is_missing_long_enough():
    monitor, clock, _, notices = make_monitor()

    feed(monitor, clock, NO_HAND, NO_HAND_NOTICE_AFTER_S - 0.2)
    assert notices == []
    feed(monitor, clock, NO_HAND, 5.0)

    assert len(notices) == 1


def test_a_visible_hand_rearms_the_notice():
    monitor, clock, _, notices = make_monitor()
    feed(monitor, clock, NO_HAND, NO_HAND_NOTICE_AFTER_S + 0.5)

    feed(monitor, clock, WITH_HAND, 1.0)
    feed(monitor, clock, NO_HAND, NO_HAND_NOTICE_AFTER_S + 0.5)

    assert len(notices) == 2


def test_a_brief_hand_appearance_restarts_the_wait():
    monitor, clock, _, notices = make_monitor()
    feed(monitor, clock, NO_HAND, NO_HAND_NOTICE_AFTER_S - 0.5)
    feed(monitor, clock, WITH_HAND, 0.1)

    feed(monitor, clock, NO_HAND, NO_HAND_NOTICE_AFTER_S - 0.5)

    assert notices == []


def test_no_notice_while_paused_or_off():
    monitor, clock, controller, notices = make_monitor()
    controller.pause()
    feed(monitor, clock, NO_HAND, NO_HAND_NOTICE_AFTER_S * 2)
    controller.stop()
    feed(monitor, clock, NO_HAND, NO_HAND_NOTICE_AFTER_S * 2)

    assert notices == []


def test_waiting_starts_over_after_a_pause():
    monitor, clock, controller, notices = make_monitor()
    feed(monitor, clock, NO_HAND, NO_HAND_NOTICE_AFTER_S - 0.5)
    controller.pause()
    feed(monitor, clock, NO_HAND, 1.0)
    controller.resume()

    feed(monitor, clock, NO_HAND, NO_HAND_NOTICE_AFTER_S - 0.5)

    assert notices == []


def test_unsubscribed_listener_is_not_called():
    monitor, clock, _, _ = make_monitor()
    calls = []
    unsubscribe = monitor.subscribe(lambda: calls.append(True))

    unsubscribe()
    feed(monitor, clock, NO_HAND, NO_HAND_NOTICE_AFTER_S + 1)

    assert calls == []
