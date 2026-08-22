from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np


# A short session-only window limits false matches after a long absence.
IDENTITY_RETENTION_SECONDS = 60.0
IDENTITY_MATCH_THRESHOLD = 0.92


@dataclass
class PersistentPerson:
    person_id: int
    features: np.ndarray
    current_track_id: Optional[int]
    last_seen: float
    last_bbox: Tuple[int, int, int, int]


def extract_person_features(frame: np.ndarray, bbox: Sequence[int]) -> Optional[np.ndarray]:
    """Return a lightweight appearance signature for one person crop."""
    if frame is None or frame.size == 0 or len(bbox) != 4:
        return None

    height, width = frame.shape[:2]
    x1, y1, x2, y2 = (int(value) for value in bbox)
    x1 = max(0, min(width, x1))
    y1 = max(0, min(height, y1))
    x2 = max(0, min(width, x2))
    y2 = max(0, min(height, y2))
    if x2 <= x1 or y2 <= y1:
        return None

    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    resized = cv2.resize(crop, (32, 64), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
    histogram = cv2.calcHist([hsv], [0, 1], None, [16, 8], [0, 180, 0, 256])
    histogram = cv2.normalize(histogram, histogram).flatten().astype(np.float32)
    return histogram


def feature_similarity(first: np.ndarray, second: np.ndarray) -> float:
    """Compare normalized appearance signatures using histogram correlation."""
    if (
        first is None
        or second is None
        or first.size == 0
        or second.size == 0
        or first.shape != second.shape
    ):
        return -1.0
    return float(cv2.compareHist(first, second, cv2.HISTCMP_CORREL))


class PersonIdentityRegistry:
    """Camera-local, session-only mapping from temporary tracks to person IDs."""

    def __init__(
        self,
        retention_seconds: float = IDENTITY_RETENTION_SECONDS,
        match_threshold: float = IDENTITY_MATCH_THRESHOLD,
    ):
        self.retention_seconds = retention_seconds
        self.match_threshold = match_threshold
        self._identities: Dict[int, PersistentPerson] = {}
        self._track_to_person: Dict[int, int] = {}
        self._next_person_id = 1

    def clear(self) -> None:
        self._identities.clear()
        self._track_to_person.clear()
        self._next_person_id = 1

    def _expire(self, now: float) -> None:
        expired_ids = [
            person_id
            for person_id, identity in self._identities.items()
            if now - identity.last_seen > self.retention_seconds
        ]
        for person_id in expired_ids:
            self._identities.pop(person_id, None)

    def assign(
        self,
        tracks: Sequence[object],
        frame: np.ndarray,
        now: Optional[float] = None,
    ) -> Dict[int, int]:
        """Assign display identities to current person tracks conservatively."""
        now = time.time() if now is None else now
        self._expire(now)
        visible_track_ids = {
            int(track.track_id)
            for track in tracks
            if getattr(track, "track_id", None) is not None
        }
        for track_id, person_id in list(self._track_to_person.items()):
            if track_id not in visible_track_ids:
                identity = self._identities.get(person_id)
                if identity is not None and identity.current_track_id == track_id:
                    identity.current_track_id = None
                del self._track_to_person[track_id]

        assignments: Dict[int, int] = {}
        reserved_person_ids = set()
        for track in tracks:
            track_id = getattr(track, "track_id", None)
            if track_id is None:
                continue
            track_id = int(track_id)
            features = extract_person_features(frame, getattr(track, "bbox", []))
            existing_person_id = self._track_to_person.get(track_id)
            if existing_person_id is not None and existing_person_id in self._identities:
                identity = self._identities[existing_person_id]
                identity.current_track_id = track_id
                identity.last_seen = now
                identity.last_bbox = tuple(int(value) for value in track.bbox)
                assignments[track_id] = existing_person_id
                reserved_person_ids.add(existing_person_id)
                continue

            best_person_id = None
            best_similarity = self.match_threshold
            if features is not None:
                for person_id, identity in self._identities.items():
                    if identity.current_track_id is not None or person_id in reserved_person_ids:
                        continue
                    similarity = feature_similarity(features, identity.features)
                    if similarity >= best_similarity:
                        best_similarity = similarity
                        best_person_id = person_id

            if best_person_id is None:
                best_person_id = self._next_person_id
                self._next_person_id += 1
                if features is None:
                    features = np.empty(0, dtype=np.float32)
                self._identities[best_person_id] = PersistentPerson(
                    person_id=best_person_id,
                    features=features,
                    current_track_id=track_id,
                    last_seen=now,
                    last_bbox=tuple(int(value) for value in track.bbox),
                )
            else:
                identity = self._identities[best_person_id]
                identity.current_track_id = track_id
                identity.last_seen = now
                identity.last_bbox = tuple(int(value) for value in track.bbox)
                if features is not None:
                    identity.features = features

            self._track_to_person[track_id] = best_person_id
            assignments[track_id] = best_person_id
            reserved_person_ids.add(best_person_id)

        return assignments

    @property
    def identities(self) -> Dict[int, PersistentPerson]:
        return self._identities
