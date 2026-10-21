"""Hand landmark detection with MediaPipe Hands (F2). The model ships inside the package: fully offline."""

import cv2
import mediapipe as mp

from jestkontrol.application.ports import Frame
from jestkontrol.domain.landmarks import Handedness, HandFrame, Point

_HANDEDNESS = {"Left": Handedness.LEFT, "Right": Handedness.RIGHT}


class MediaPipeHandTracker:
    def __init__(
        self,
        min_detection_confidence: float = 0.6,
        min_tracking_confidence: float = 0.5,
        model_complexity: int = 1,
    ) -> None:
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def detect(self, frame: Frame) -> HandFrame | None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False  # lets MediaPipe skip a defensive copy
        result = self._hands.process(rgb)
        if not result.multi_hand_landmarks:
            return None
        landmarks = result.multi_hand_landmarks[0].landmark
        classification = result.multi_handedness[0].classification[0]
        return HandFrame(
            tuple(Point(l.x, l.y) for l in landmarks),
            classification.score,
            _HANDEDNESS.get(classification.label),
        )

    def close(self) -> None:
        self._hands.close()
