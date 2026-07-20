"""경로 변주(mutation) 모듈.

정상 경로를 변형하여 다양한 테스트 시나리오를 생성합니다:
- detour: 경로 이탈 (재탐색 유도)
- stop: 정차 (동일 좌표 반복)
- overspeed: 과속 (포인트 간격 확대)
"""

import math
import random


def apply_detour(
    coordinates: list[tuple[float, float]],
    detour_index: int | None = None,
    offset_meters: float = 200.0,
) -> list[tuple[float, float]]:
    """경로 중간 지점을 옆으로 이탈시켜 재탐색을 유도.

    Args:
        coordinates: 원본 좌표 리스트.
        detour_index: 이탈시킬 포인트 인덱스 (None이면 중간 지점).
        offset_meters: 이탈 거리 (미터).

    Returns:
        변형된 좌표 리스트.
    """
    if len(coordinates) < 3:
        return list(coordinates)

    result = list(coordinates)
    if detour_index is None:
        detour_index = len(result) // 2

    detour_index = max(1, min(detour_index, len(result) - 2))

    lat, lng = result[detour_index]

    # 경로 진행 방향에 수직으로 오프셋
    prev_lat, prev_lng = result[detour_index - 1]
    dlat = lat - prev_lat
    dlng = lng - prev_lng

    # 수직 벡터 (90도 회전)
    perp_dlat = -dlng
    perp_dlng = dlat

    # 정규화 후 오프셋 적용 (대략적 미터 → 도 변환)
    length = math.sqrt(perp_dlat**2 + perp_dlng**2)
    if length < 1e-10:
        # 방향을 구할 수 없으면 랜덤 방향
        angle = random.uniform(0, 2 * math.pi)
        perp_dlat = math.cos(angle)
        perp_dlng = math.sin(angle)
        length = 1.0

    # 위도 1도 ≈ 111,320m, 경도 1도 ≈ 111,320m * cos(lat)
    meters_per_deg_lat = 111_320.0
    meters_per_deg_lng = 111_320.0 * math.cos(math.radians(lat))

    offset_lat = (perp_dlat / length) * (offset_meters / meters_per_deg_lat)
    offset_lng = (perp_dlng / length) * (offset_meters / meters_per_deg_lng)

    # 이탈 구간: 이탈 → 유지 → 복귀 (자연스러운 이탈 경로)
    span = max(3, len(result) // 10)
    start = max(1, detour_index - span // 2)
    end = min(len(result) - 1, detour_index + span // 2)

    for i in range(start, end + 1):
        # 이탈 강도: 중심에서 가장 강하고 양쪽으로 감소
        t = 1.0 - abs(i - detour_index) / (span / 2 + 1)
        t = max(0.0, t)
        orig_lat, orig_lng = result[i]
        result[i] = (orig_lat + offset_lat * t, orig_lng + offset_lng * t)

    return result


def apply_stop(
    coordinates: list[tuple[float, float]],
    stop_index: int | None = None,
    duration_seconds: int = 10,
) -> list[tuple[float, float]]:
    """특정 지점에서 정차를 시뮬레이션 (동일 좌표 반복 삽입).

    Args:
        coordinates: 원본 좌표 리스트.
        stop_index: 정차 지점 인덱스 (None이면 중간 지점).
        duration_seconds: 정차 시간 (초).

    Returns:
        정차 구간이 삽입된 좌표 리스트.
    """
    if not coordinates:
        return []

    result = list(coordinates)
    if stop_index is None:
        stop_index = len(result) // 2

    stop_index = max(0, min(stop_index, len(result) - 1))
    stop_point = result[stop_index]

    # 정차 지점에 동일 좌표를 반복 삽입
    for _ in range(duration_seconds):
        result.insert(stop_index + 1, stop_point)

    return result


def apply_overspeed(
    coordinates: list[tuple[float, float]],
    speed_multiplier: float = 2.0,
) -> list[tuple[float, float]]:
    """포인트를 솎아내어 과속 주행을 시뮬레이션.

    Args:
        coordinates: 원본 좌표 리스트 (1초 간격).
        speed_multiplier: 속도 배율 (2.0이면 2배속 → 포인트 절반).

    Returns:
        솎아낸 좌표 리스트.
    """
    if len(coordinates) < 2 or speed_multiplier <= 1.0:
        return list(coordinates)

    step = speed_multiplier
    result: list[tuple[float, float]] = []
    i = 0.0
    while int(i) < len(coordinates):
        result.append(coordinates[int(i)])
        i += step

    # 마지막 포인트 보장
    if result[-1] != coordinates[-1]:
        result.append(coordinates[-1])

    return result
