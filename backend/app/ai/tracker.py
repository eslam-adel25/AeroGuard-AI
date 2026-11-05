import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import threading


def iou(boxA, boxB):
    # box = [x1,y1,x2,y2]
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interW = max(0, xB - xA)
    interH = max(0, yB - yA)
    interArea = interW * interH
    boxAArea = max(0, boxA[2] - boxA[0]) * max(0, boxA[3] - boxA[1])
    boxBArea = max(0, boxB[2] - boxB[0]) * max(0, boxB[3] - boxB[1])
    denom = float(boxAArea + boxBArea - interArea)
    if denom <= 0:
        return 0.0
    return interArea / denom


@dataclass
class Track:
    track_id: int
    class_name: str
    confidence: float
    bbox: List[int]
    center_point: List[int]
    first_seen: float
    last_seen: float
    lost_frames: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


class IoUTracker:
    """A simple IoU-based tracker used as a fallback.

    This is intentionally lightweight and is only the default implementation
    when a production tracker (ByteTrack/DeepSORT) isn't installed.
    The TrackerManager provides a stable interface so this can be swapped
    without changing other code.
    """
    def __init__(self, max_lost: int = 30, iou_threshold: float = 0.35):
        self.max_lost = max_lost
        self.iou_threshold = iou_threshold
        self._tracks: Dict[int, Track] = {}
        self._next_id = 1
        self._lock = threading.RLock()

    def initialize(self):
        with self._lock:
            self._tracks.clear()
            self._next_id = 1

    def reset(self):
        self.initialize()

    def _create_track(self, det):
        t = Track(
            track_id=self._next_id,
            class_name=det["class_name"],
            confidence=det["confidence"],
            bbox=det["bbox"],
            center_point=[int((det["bbox"][0] + det["bbox"][2]) / 2), int((det["bbox"][1] + det["bbox"][3]) / 2)],
            first_seen=time.time(),
            last_seen=time.time(),
            lost_frames=0,
        )
        self._tracks[self._next_id] = t
        self._next_id += 1
        return t

    def update(self, detections: List[Dict[str, Any]]) -> List[Track]:
        """Update tracks with a list of detections.

        detections: list of dicts {bbox:[x1,y1,x2,y2], class_name: str, confidence: float}
        Returns list of active Track objects (matched + newly created)
        """
        with self._lock:
            assigned = set()
            det_assigned = [False] * len(detections)

            track_ids = list(self._tracks.keys())
            # compute IoU matrix and greedily match
            for tid in track_ids:
                track = self._tracks.get(tid)
                if track is None:
                    continue
                best_iou = 0.0
                best_idx = -1
                for i, det in enumerate(detections):
                    if det_assigned[i]:
                        continue
                    score = iou(track.bbox, det["bbox"])
                    if score > best_iou:
                        best_iou = score
                        best_idx = i
                if best_idx >= 0 and best_iou >= self.iou_threshold:
                    det = detections[best_idx]
                    # update track
                    track.bbox = det["bbox"]
                    track.center_point = [int((track.bbox[0] + track.bbox[2]) / 2), int((track.bbox[1] + track.bbox[3]) / 2)]
                    track.confidence = det.get("confidence", track.confidence)
                    track.class_name = det.get("class_name", track.class_name)
                    track.last_seen = time.time()
                    track.lost_frames = 0
                    assigned.add(tid)
                    det_assigned[best_idx] = True

            # create tracks for unassigned detections
            for i, det in enumerate(detections):
                if not det_assigned[i]:
                    track = self._create_track(det)
                    assigned.add(track.track_id)

            # increment lost_frames for unassigned tracks
            for tid, track in list(self._tracks.items()):
                if tid not in assigned:
                    track.lost_frames += 1
                    # mark last_seen remains same
                if track.lost_frames > self.max_lost:
                    # remove track
                    del self._tracks[tid]

            # return current active tracks
            return list(self._tracks.values())

    def get_active_tracks(self) -> List[Track]:
        with self._lock:
            return [t for t in self._tracks.values() if t.lost_frames == 0]


class TrackerManager:
    """Facade that keeps a stable API and allows swapping underlying trackers."""
    def __init__(self, backend: Optional[str] = None, **kwargs):
        # backend: 'bytetrack', 'deepsort', 'botsort' or None
        self.backend = backend
        self._impl = None
        # try to instantiate requested backend; fallback to IoUTracker
        backend_choice = (backend or "iou").lower()
        if backend_choice == "bytetrack":
            try:
                # Attempt to import a ByteTrack adapter (if dependency available)
                from .bytetrack_adapter import ByteTrackAdapter  # type: ignore

                self._impl = ByteTrackAdapter(**kwargs)
            except Exception:
                print("[TrackerManager] ByteTrack adapter unavailable, falling back to IoUTracker")
        elif backend_choice == "deepsort":
            try:
                from .deepsort_adapter import DeepSortAdapter  # type: ignore

                self._impl = DeepSortAdapter(**kwargs)
            except Exception:
                print("[TrackerManager] DeepSORT adapter unavailable, falling back to IoUTracker")

        if self._impl is None:
            # final fallback
            self._impl = IoUTracker(**kwargs)

    def initialize(self):
        self._impl.initialize()

    def update(self, detections: List[Dict[str, Any]]) -> List[Track]:
        return self._impl.update(detections)

    def get_active_tracks(self) -> List[Track]:
        return self._impl.get_active_tracks()

    def reset(self):
        self._impl.reset()
