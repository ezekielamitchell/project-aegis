"""Tests for the temporal verification layer — the core contribution."""

from aegis.types import Detection, DetectionState
from aegis.verification import TemporalFilter


def make_detection(cx: float = 320.0) -> Detection:
    return Detection(class_name="person", confidence=0.9, bbox=(cx - 40, 180, cx + 40, 300))


def test_starts_with_no_target():
    tf = TemporalFilter(required_consecutive_frames=4)
    assert tf.state == DetectionState.NO_TARGET


def test_single_detection_is_only_candidate():
    tf = TemporalFilter(required_consecutive_frames=4)
    assert tf.update(make_detection()) == DetectionState.CANDIDATE


def test_confirmation_requires_n_consecutive_frames():
    tf = TemporalFilter(required_consecutive_frames=4)
    states = [tf.update(make_detection()) for _ in range(4)]
    assert states[:3] == [DetectionState.CANDIDATE] * 3
    assert states[3] == DetectionState.CONFIRMED


def test_unstable_geometry_resets_count():
    tf = TemporalFilter(required_consecutive_frames=3, max_centroid_drift=0.1)
    tf.update(make_detection(cx=100))
    tf.update(make_detection(cx=110))
    # Big jump across the frame — should not count toward confirmation.
    tf.update(make_detection(cx=600))
    assert tf.state == DetectionState.CANDIDATE


def test_confirmed_target_becomes_lost_after_max_missed():
    tf = TemporalFilter(required_consecutive_frames=2, max_missed_frames=3)
    tf.update(make_detection())
    tf.update(make_detection())
    assert tf.state == DetectionState.CONFIRMED
    for _ in range(3):
        assert tf.update(None) == DetectionState.CONFIRMED
    assert tf.update(None) == DetectionState.LOST


def test_candidate_dropped_when_detection_disappears():
    tf = TemporalFilter(required_consecutive_frames=4)
    tf.update(make_detection())
    assert tf.update(None) == DetectionState.NO_TARGET


def test_false_positive_rate_tracked():
    tf = TemporalFilter(required_consecutive_frames=4)
    tf.update(make_detection())
    assert 0.0 <= tf.false_positive_rate <= 1.0
