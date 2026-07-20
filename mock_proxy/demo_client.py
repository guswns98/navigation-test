"""OSRM 라우팅 API를 호출하는 데모 클라이언트.

Mock Proxy를 통해 장애 주입 테스트를 수행하기 위한 통제 가능한 클라이언트.
프록시 설정 시 mitmproxy를 경유하여 응답이 변조됩니다.

사용법:
    # 직접 호출 (프록시 없이)
    client = RouteClient()
    result = client.get_route((37.5665, 126.9780), (37.4979, 127.0276))

    # 프록시 경유
    client = RouteClient(proxy="http://127.0.0.1:8080")
    result = client.get_route((37.5665, 126.9780), (37.4979, 127.0276))
"""

import requests


class RouteClientError(Exception):
    """라우팅 API 호출 실패."""


class RouteClient:
    """OSRM 라우팅 API 클라이언트."""

    BASE_URL = "http://router.project-osrm.org"
    DEFAULT_TIMEOUT = 5

    def __init__(
        self,
        proxy: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.session = requests.Session()
        self.timeout = timeout
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}
            # mitmproxy 인증서 검증 비활성화
            self.session.verify = False

    def get_route(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> dict:
        """경로 조회.

        Args:
            origin: 출발지 (lat, lng).
            destination: 도착지 (lat, lng).

        Returns:
            OSRM API 응답 dict.

        Raises:
            RouteClientError: API 호출 실패 또는 비정상 응답.
        """
        coords = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
        url = f"{self.BASE_URL}/route/v1/driving/{coords}"
        params = {"overview": "full", "geometries": "geojson"}

        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
        except requests.Timeout:
            raise RouteClientError("요청 타임아웃")
        except requests.ConnectionError as e:
            raise RouteClientError(f"연결 실패: {e}")

        if resp.status_code != 200:
            raise RouteClientError(
                f"HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            data = resp.json()
        except ValueError:
            raise RouteClientError(f"JSON 파싱 실패: {resp.text[:200]}")

        if data.get("code") != "Ok":
            raise RouteClientError(f"API 에러: {data.get('code')}")

        routes = data.get("routes", [])
        if not routes:
            raise RouteClientError("경로 없음: routes 배열이 비어있음")

        geometry = routes[0].get("geometry")
        if geometry is None:
            raise RouteClientError("경로 데이터 손상: geometry가 null")

        return data

    def get_route_coordinates(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> list[tuple[float, float]]:
        """경로 좌표 리스트 반환.

        Returns:
            (lat, lng) 튜플 리스트.
        """
        data = self.get_route(origin, destination)
        coords = data["routes"][0]["geometry"]["coordinates"]
        return [(c[1], c[0]) for c in coords]
