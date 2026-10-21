"""CPU-only launch barriers; never starts GPU training or remote processes."""
import unittest
from unittest.mock import Mock, patch

from tools.g1_04_coordinate import start_control_pair, start_training_pair


class G104CoordinateTests(unittest.TestCase):
    def test_control_launch_starts_source_polls_listener_then_starts_client(self):
        events = []

        def start_source():
            events.append("source-start")
            return "source-handle"

        def source_listening():
            events.append("listener-poll")
            return True

        def start_reference():
            events.append("client-start")
            return "client-handle"

        result = start_control_pair(
            start_source, source_listening, start_reference, timeout_s=1
        )

        self.assertEqual(result, ("source-handle", "client-handle"))
        self.assertEqual(events, ["source-start", "listener-poll", "client-start"])

    def test_listener_timeout_never_starts_client_without_sleeping(self):
        events = []

        def start_source():
            events.append("source-start")

        def source_listening():
            events.append("listener-poll")
            return False

        def start_reference():
            events.append("client-start")

        with patch("tools.g1_04_coordinate.time.monotonic", side_effect=[12.0, 13.0]), \
                patch("tools.g1_04_coordinate.time.sleep") as sleep:
            with self.assertRaises(TimeoutError):
                start_control_pair(start_source, source_listening, start_reference, timeout_s=1)

        self.assertEqual(events, ["source-start", "listener-poll"])
        sleep.assert_not_called()

    def test_training_does_not_start_when_preflight_is_not_pass(self):
        events = []
        verify = Mock(side_effect=lambda: events.append("preflight") or False)
        sidecars = Mock(side_effect=lambda: events.append("sidecars") or True)
        start_reference = Mock(side_effect=lambda: events.append("reference-start"))
        start_source = Mock(side_effect=lambda: events.append("source-start"))

        with self.assertRaises(ValueError):
            start_training_pair(verify, sidecars, start_reference, start_source)

        self.assertEqual(events, ["preflight"])
        verify.assert_called_once_with()
        sidecars.assert_not_called()
        start_reference.assert_not_called()
        start_source.assert_not_called()

    def test_training_does_not_start_when_both_sidecars_are_not_ready(self):
        events = []
        verify = Mock(side_effect=lambda: events.append("preflight") or True)
        sidecars = Mock(side_effect=lambda: events.append("sidecars") or False)
        start_reference = Mock(side_effect=lambda: events.append("reference-start"))
        start_source = Mock(side_effect=lambda: events.append("source-start"))

        with self.assertRaises(ValueError):
            start_training_pair(verify, sidecars, start_reference, start_source)

        self.assertEqual(events, ["preflight", "sidecars"])
        verify.assert_called_once_with()
        sidecars.assert_called_once_with()
        start_reference.assert_not_called()
        start_source.assert_not_called()

    def test_training_launches_each_rank_once_only_after_both_gates_pass(self):
        events = []
        verify = Mock(side_effect=lambda: events.append("preflight") or True)
        sidecars = Mock(side_effect=lambda: events.append("sidecars") or True)
        start_reference = Mock(side_effect=lambda: events.append("reference-start") or "ref")
        start_source = Mock(side_effect=lambda: events.append("source-start") or "src")

        result = start_training_pair(verify, sidecars, start_reference, start_source)

        self.assertEqual(result, ("ref", "src"))
        self.assertEqual(events, ["preflight", "sidecars", "reference-start", "source-start"])
        verify.assert_called_once_with()
        sidecars.assert_called_once_with()
        start_reference.assert_called_once_with()
        start_source.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
