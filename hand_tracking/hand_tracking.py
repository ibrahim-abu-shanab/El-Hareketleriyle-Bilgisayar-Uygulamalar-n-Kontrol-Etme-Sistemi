"""Week 3: webcam + MediaPipe hand landmarks. Press Q to exit."""
import time
from pathlib import Path
from urllib.request import urlretrieve

import cv2
import mediapipe as mp

MODEL_URL = (
    'https://storage.googleapis.com/mediapipe-models/hand_landmarker/'
    'hand_landmarker/float16/1/hand_landmarker.task'
)
MODEL_PATH = Path(__file__).resolve().parent / 'hand_landmarker.task'

# MediaPipe anatomical connections among 21 landmarks.
CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),
]


def load_model():
    if not MODEL_PATH.exists():
        print('Downloading official MediaPipe hand model (first run only)...')
        try:
            urlretrieve(MODEL_URL, MODEL_PATH)
        except Exception as error:
            MODEL_PATH.unlink(missing_ok=True)
            raise RuntimeError(
                'Could not download hand_landmarker.task. Check internet connection. '
                f'Download manually from: {MODEL_URL}'
            ) from error
    return str(MODEL_PATH)


def draw_hand(frame, landmarks):
    height, width = frame.shape[:2]
    points = [(int(p.x * width), int(p.y * height)) for p in landmarks]
    for first, second in CONNECTIONS:
        cv2.line(frame, points[first], points[second], (0, 210, 0), 2)
    for index, (x, y) in enumerate(points):
        cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)
        if index in (0, 4, 8, 12, 16, 20):
            cv2.putText(frame, str(index), (x + 7, y - 7),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    return points


def main():
    model_path = load_model()
    camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not camera.isOpened():
        camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        raise RuntimeError('Webcam unavailable. Check camera permissions / other apps.')

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    options = mp.tasks.vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=model_path),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    started = time.perf_counter()
    previous = started
    last_timestamp_ms = -1
    try:
        with mp.tasks.vision.HandLandmarker.create_from_options(options) as detector:
            while True:
                ok, frame = camera.read()
                if not ok:
                    print('Could not read camera frame.')
                    break
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                timestamp_ms = max(int((time.perf_counter() - started) * 1000), last_timestamp_ms + 1)
                last_timestamp_ms = timestamp_ms
                result = detector.detect_for_video(mp_image, timestamp_ms)

                if result.hand_landmarks:
                    points = draw_hand(frame, result.hand_landmarks[0])
                    index_x, index_y = points[8]
                    cv2.putText(frame, f'Hand detected | 21 points', (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.67, (0, 255, 0), 2)
                    cv2.putText(frame, f'Index fingertip: ({index_x}, {index_y})', (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    # Coordinates ready for Yasser's gesture-recognition module:
                    # result.hand_landmarks[0][8].x / .y are normalized to [0, 1].
                else:
                    cv2.putText(frame, 'No hand detected', (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                now = time.perf_counter()
                fps = 1 / max(now - previous, 1e-6)
                previous = now
                cv2.putText(frame, f'FPS: {fps:.1f}', (10, frame.shape[0] - 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.imshow('Week 3 - Ibrahim - Hand Detection', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
