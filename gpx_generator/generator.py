"""OSRM API로 경로를 생성하고 GPX 파일로 출력하는 모듈."""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import gpxpy
import gpxpy.gpx
import requests

logger = logging.getLogger(__name__)

OSRM_BASE_URL = "http://router.project-osrm.org/route/v1/driving"


def fetch_route(
    origin: tuple[float, float],
    destination: tuple[float, float],
) -> list[tuple[float, float]]:
    """OSRM API를 호출하여 경로 좌표열을 반환.

    Args:
        origin: 출발지 (lat, lng).
        destination: 도착지 (lat, lng).

    Returns:
        (lat, lng) 튜플 리스트.
    """
    # OSRM은 lng,lat 순서
    coords = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
    url = f"{OSRM_BASE_URL}/{coords}"
    params = {"overview": "full", "geometries": "geojson"}

    logger.info("OSRM 경로 요청: %s → %s", origin, destination)
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError(f"OSRM 경로 생성 실패: {data.get('code', 'Unknown')}")

    # GeoJSON coordinates: [lng, lat] → (lat, lng)
    geojson_coords = data["routes"][0]["geometry"]["coordinates"]
    route = [(coord[1], coord[0]) for coord in geojson_coords]

    logger.info("경로 수신 완료: %d 좌표", len(route))
    return route


def generate_gpx(
    coordinates: list[tuple[float, float]],
    output_path: str | Path,
    start_time: datetime | None = None,
) -> Path:
    """좌표 리스트를 GPX 파일로 출력.

    Args:
        coordinates: (lat, lng) 리스트 (보간 완료된 1초 간격 좌표).
        output_path: 출력 파일 경로.
        start_time: 첫 포인트 시각 (기본: 현재 시각).

    Returns:
        생성된 GPX 파일 경로.
    """
    if start_time is None:
        start_time = datetime.now(timezone.utc)

    gpx = gpxpy.gpx.GPX()
    track = gpxpy.gpx.GPXTrack(name="TMAP QA Route")
    gpx.tracks.append(track)

    segment = gpxpy.gpx.GPXTrackSegment()
    track.segments.append(segment)

    for i, (lat, lng) in enumerate(coordinates):
        point = gpxpy.gpx.GPXTrackPoint(
            latitude=lat,
            longitude=lng,
            time=start_time + timedelta(seconds=i),
        )
        segment.points.append(point)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(gpx.to_xml(), encoding="utf-8")

    logger.info("GPX 생성 완료: %s (%d 포인트)", output_path, len(coordinates))
    return output_path
