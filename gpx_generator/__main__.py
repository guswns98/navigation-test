"""GPX Generator CLI 진입점.

사용법:
    python -m gpx_generator --from 37.5665,126.9780 --to 37.4979,127.0276 --speed 60 --mutation normal --output route.gpx
"""

import argparse
import logging
import sys

from gpx_generator.generator import fetch_route, generate_gpx
from gpx_generator.interpolate import interpolate_route
from gpx_generator.mutations import apply_detour, apply_overspeed, apply_stop


def parse_coord(value: str) -> tuple[float, float]:
    """'lat,lng' 문자열을 (lat, lng) 튜플로 파싱."""
    parts = value.split(",")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"좌표는 'lat,lng' 형식이어야 합니다: {value}")
    return (float(parts[0]), float(parts[1]))


MUTATIONS = {
    "normal": None,
    "detour": apply_detour,
    "stop": apply_stop,
    "overspeed": apply_overspeed,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OSRM 기반 GPX 경로 생성기",
    )
    parser.add_argument(
        "--from", dest="origin", type=parse_coord, required=True,
        help="출발지 좌표 (lat,lng)",
    )
    parser.add_argument(
        "--to", dest="destination", type=parse_coord, required=True,
        help="도착지 좌표 (lat,lng)",
    )
    parser.add_argument(
        "--speed", type=float, default=60.0,
        help="목표 속도 km/h (기본: 60)",
    )
    parser.add_argument(
        "--mutation", choices=MUTATIONS.keys(), default="normal",
        help="시나리오 변주 (기본: normal)",
    )
    parser.add_argument(
        "--output", "-o", default="route.gpx",
        help="출력 GPX 파일 경로 (기본: route.gpx)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="상세 로그 출력",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 1. OSRM 경로 생성
    raw_route = fetch_route(args.origin, args.destination)
    print(f"경로 수신: {len(raw_route)} 좌표")

    # 2. 속도 기반 보간
    interpolated = interpolate_route(raw_route, speed_kmh=args.speed)
    print(f"보간 완료: {len(interpolated)} 포인트 ({args.speed} km/h 기준)")

    # 3. 시나리오 변주 적용
    mutation_fn = MUTATIONS[args.mutation]
    if mutation_fn is not None:
        final_route = mutation_fn(interpolated)
        print(f"변주 적용: {args.mutation} → {len(final_route)} 포인트")
    else:
        final_route = interpolated

    # 4. GPX 출력
    output = generate_gpx(final_route, args.output)
    print(f"GPX 생성 완료: {output}")
    print(f"예상 소요 시간: {len(final_route)}초 ({len(final_route) / 60:.1f}분)")


if __name__ == "__main__":
    main()
