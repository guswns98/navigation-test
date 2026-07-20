"""속도 기반 경로 보간 모듈.

두 좌표 사이를 목표 속도에 맞게 1초 간격 포인트로 분할합니다.
예: 60km/h → 약 16.7m/s 간격.
"""

import math

# 지구 반지름 (미터)
EARTH_RADIUS_M = 6_371_000


def _haversine(
    lat1: float, lng1: float, lat2: float, lng2: float
) -> float:
    """두 좌표 사이의 거리를 미터 단위로 계산 (Haversine 공식)."""
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _lerp(
    lat1: float, lng1: float, lat2: float, lng2: float, t: float
) -> tuple[float, float]:
    """선형 보간. t=0.0 → (lat1,lng1), t=1.0 → (lat2,lng2)."""
    return (
        lat1 + (lat2 - lat1) * t,
        lng1 + (lng2 - lng1) * t,
    )


def interpolate_route(
    coordinates: list[tuple[float, float]],
    speed_kmh: float = 60.0,
) -> list[tuple[float, float]]:
    """좌표열을 목표 속도에 맞게 1초 간격으로 보간.

    Args:
        coordinates: 원본 경로 좌표 (lat, lng) 리스트.
        speed_kmh: 목표 속도 (km/h).

    Returns:
        1초 간격으로 보간된 좌표 리스트.
    """
    if len(coordinates) < 2:
        return list(coordinates)

    speed_mps = speed_kmh * 1000.0 / 3600.0  # m/s
    result: list[tuple[float, float]] = [coordinates[0]]

    for i in range(len(coordinates) - 1):
        lat1, lng1 = coordinates[i]
        lat2, lng2 = coordinates[i + 1]

        segment_dist = _haversine(lat1, lng1, lat2, lng2)
        if segment_dist < 0.1:  # 0.1m 미만은 스킵
            continue

        # 이 구간을 주행하는 데 걸리는 시간 (초)
        travel_time = segment_dist / speed_mps
        num_steps = max(1, int(travel_time))

        for step in range(1, num_steps + 1):
            t = step / num_steps
            result.append(_lerp(lat1, lng1, lat2, lng2, t))

    return result
