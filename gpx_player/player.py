"""GPX 파일을 파싱하여 에뮬레이터/실기기에 좌표를 주입하는 플레이어."""

import logging
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

import gpxpy

logger = logging.getLogger(__name__)


class LocationBackend(ABC):
    """좌표 주입 백엔드 추상 클래스."""

    @abstractmethod
    def set_location(self, lat: float, lng: float, alt: float = 0.0) -> None: ...


class AdbBackend(LocationBackend):
    """adb emu geo fix 기반 좌표 주입 (에뮬레이터 전용).

    주의: geo fix 인자 순서는 경도(lng), 위도(lat) 순입니다.
    """

    def set_location(self, lat: float, lng: float, alt: float = 0.0) -> None:
        # geo fix 인자 순서: longitude latitude [altitude]
        subprocess.run(
            ["adb", "emu", "geo", "fix", str(lng), str(lat), str(alt)],
            check=True,
            capture_output=True,
        )


class AppiumBackend(LocationBackend):
    """Appium driver.set_location() 기반 좌표 주입 (실기기 확장용)."""

    def __init__(self, driver) -> None:
        self.driver = driver

    def set_location(self, lat: float, lng: float, alt: float = 0.0) -> None:
        self.driver.set_location(lat, lng, alt)


class GpxPlayer:
    """GPX 파일을 파싱하여 1초 간격으로 좌표를 주입하는 플레이어.

    Args:
        gpx_path: GPX 파일 경로.
        backend: 좌표 주입 백엔드 (AdbBackend 또는 AppiumBackend).
        speed_multiplier: 재생 속도 배율 (2.0이면 2배속, 간격이 절반).
    """

    def __init__(
        self,
        gpx_path: str | Path,
        backend: LocationBackend,
        speed_multiplier: float = 1.0,
    ) -> None:
        self.gpx_path = Path(gpx_path)
        self.backend = backend
        self.speed_multiplier = speed_multiplier
        self._points: list[tuple[float, float, float]] = self._parse_gpx()
        self._stop_event = threading.Event()
        self._current_index = 0
        self._playing = False

    def _parse_gpx(self) -> list[tuple[float, float, float]]:
        """GPX 파일에서 (lat, lng, elevation) 리스트 추출."""
        with open(self.gpx_path) as f:
            gpx = gpxpy.parse(f)

        points: list[tuple[float, float, float]] = []
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points.append((
                        point.latitude,
                        point.longitude,
                        point.elevation or 0.0,
                    ))
        logger.info("GPX 로드 완료: %d 포인트 (%s)", len(points), self.gpx_path.name)
        return points

    def play(self, callback: Callable[[int, float, float, float], None] | None = None) -> None:
        """동기 재생 — 모든 포인트를 순차 주입.

        Args:
            callback: 각 포인트 주입 후 호출. (index, lat, lng, alt) 인자.
        """
        self._stop_event.clear()
        self._playing = True
        interval = 1.0 / self.speed_multiplier

        try:
            for i, (lat, lng, alt) in enumerate(self._points):
                if self._stop_event.is_set():
                    logger.info("재생 중지 (index=%d/%d)", i, len(self._points))
                    break

                self._current_index = i
                self.backend.set_location(lat, lng, alt)
                logger.debug(
                    "[%d/%d] lat=%.6f, lng=%.6f",
                    i + 1, len(self._points), lat, lng,
                )

                if callback:
                    callback(i, lat, lng, alt)

                if i < len(self._points) - 1:
                    time.sleep(interval)
        finally:
            self._playing = False

    def play_async(
        self, callback: Callable[[int, float, float, float], None] | None = None
    ) -> threading.Thread:
        """비동기 재생 — 백그라운드 스레드에서 재생, Thread 반환."""
        thread = threading.Thread(target=self.play, args=(callback,), daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        """재생 중지."""
        self._stop_event.set()

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def progress(self) -> float:
        """현재 진행률 (0.0 ~ 1.0)."""
        if not self._points:
            return 0.0
        return self._current_index / (len(self._points) - 1)

    @property
    def total_points(self) -> int:
        return len(self._points)
