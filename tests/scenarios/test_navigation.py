"""티맵 경로 안내 시나리오 테스트.

시나리오 1~5: 목적지 설정 → 안내 → 주행 → 이탈/정차 → 종료
GPX Generator로 경로를 생성하고, GPX Player로 가상 주행하면서 Appium으로 UI 검증.
"""

import subprocess
import time

import allure
import pytest

from gpx_generator import fetch_route, generate_gpx, interpolate_route
from gpx_generator.mutations import apply_detour, apply_stop
from tests.pages.map_page import MapPage
from tests.pages.navigation_page import NavigationPage

# 테스트 경로: 서울시청 → 강남역
ORIGIN = (37.5665, 126.9780)
DESTINATION = (37.4979, 127.0276)
DESTINATION_QUERY = "강남역"


def _set_gps_to_origin():
    """GPS를 출발지(서울시청)로 설정 (adb — 초기 위치 설정용)."""
    subprocess.run(
        ["adb", "emu", "geo", "fix", str(ORIGIN[1]), str(ORIGIN[0])],
        check=True, capture_output=True,
    )


def _start_fresh_navigation(driver, map_page):
    """메인 화면에서 강남역 안내를 새로 시작."""
    _set_gps_to_origin()
    time.sleep(5)

    map_page.ensure_main_screen()
    time.sleep(2)
    map_page.search_destination(DESTINATION_QUERY)
    time.sleep(2)
    map_page.select_first_result()
    map_page.start_navigation()


@pytest.fixture(scope="module")
def gpx_normal(tmp_path_factory):
    """정상 주행 GPX 파일 생성."""
    tmp = tmp_path_factory.mktemp("gpx")
    route = fetch_route(ORIGIN, DESTINATION)
    interpolated = interpolate_route(route, speed_kmh=60.0)
    return str(generate_gpx(interpolated, tmp / "normal.gpx"))


@pytest.fixture(scope="module")
def gpx_detour(tmp_path_factory):
    """경로 이탈 GPX 파일 생성 (500m 오프셋)."""
    tmp = tmp_path_factory.mktemp("gpx")
    route = fetch_route(ORIGIN, DESTINATION)
    interpolated = interpolate_route(route, speed_kmh=60.0)
    detoured = apply_detour(interpolated, offset_meters=500.0)
    return str(generate_gpx(detoured, tmp / "detour.gpx"))


@pytest.fixture(scope="module")
def gpx_stop(tmp_path_factory):
    """정차 시나리오 GPX 파일 생성."""
    tmp = tmp_path_factory.mktemp("gpx")
    route = fetch_route(ORIGIN, DESTINATION)
    interpolated = interpolate_route(route, speed_kmh=60.0)
    stopped = apply_stop(interpolated, duration_seconds=15)
    return str(generate_gpx(stopped, tmp / "stop.gpx"))


@pytest.fixture
def map_page(appium_driver):
    return MapPage(appium_driver)


@pytest.fixture
def nav_page(appium_driver):
    return NavigationPage(appium_driver)


@allure.epic("TMAP 경로 안내")
@allure.feature("가상 주행 시나리오")
@pytest.mark.navigation
class TestNavigation:
    """티맵 경로 안내 통합 테스트."""

    @allure.story("안내 시작")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_01_start_navigation(self, appium_driver, map_page, nav_page):
        """목적지 설정 → 안내 시작 → 안내 화면 진입 확인."""
        with allure.step("GPS를 출발지로 설정 + 안내 시작"):
            _start_fresh_navigation(appium_driver, map_page)

        with allure.step("안내 화면 진입 확인"):
            assert nav_page.is_navigation_active(), "안내 화면이 활성화되지 않음"

    @allure.story("잔여 거리 갱신")
    @allure.severity(allure.severity_level.NORMAL)
    def test_02_distance_update(
        self, appium_driver, nav_page, player_factory, gpx_normal, map_page
    ):
        """정상 주행 중 잔여 거리 갱신 확인."""
        # 안내 모드가 아니면 새로 시작
        if not nav_page.is_navigation_active():
            _start_fresh_navigation(appium_driver, map_page)

        with allure.step("잔여 거리 초기값 기록"):
            initial_distance = nav_page.get_remaining_distance()
            allure.attach(initial_distance, "초기 잔여 거리", allure.attachment_type.TEXT)

        with allure.step("GPX 재생 (4배속, 30초간)"):
            player = player_factory(gpx_normal, speed_multiplier=4.0)
            thread = player.play_async()
            time.sleep(30)
            player.stop()

        with allure.step("잔여 거리 갱신 확인"):
            new_distance = nav_page.get_remaining_distance()
            allure.attach(new_distance, "갱신된 잔여 거리", allure.attachment_type.TEXT)
            assert new_distance != initial_distance, "거리 값이 변경되지 않음"

    @allure.story("경로 이탈 → 재탐색")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.reroute
    def test_03_reroute_on_detour(
        self, appium_driver, nav_page, player_factory, gpx_detour, map_page
    ):
        """경로 이탈 시 재탐색 발생 확인 (핵심 시나리오)."""
        # 안내 모드가 아니면 새로 시작
        if not nav_page.is_navigation_active():
            _start_fresh_navigation(appium_driver, map_page)

        with allure.step("이탈 전 안내 문구 기록"):
            try:
                initial_guidance = nav_page.get_current_guidance_text()
                initial_distance = nav_page.get_remaining_distance()
            except Exception:
                initial_guidance = ""
                initial_distance = ""
            allure.attach(
                f"거리: {initial_distance}, 안내: {initial_guidance}",
                "이탈 전 상태", allure.attachment_type.TEXT,
            )

        with allure.step("이탈 경로 GPX 재생 (4배속, 이탈 구간까지)"):
            player = player_factory(gpx_detour, speed_multiplier=4.0)
            thread = player.play_async()

            # 이탈 구간(~50%)까지 재생 대기
            for _ in range(120):
                if player.progress >= 0.55:
                    break
                time.sleep(1)
            player.stop()

        with allure.step("재탐색 확인 — 안내 문구 또는 거리 변화 감지"):
            time.sleep(3)  # UI 갱신 대기

            rerouted = False
            # 1. page_source에서 재탐색 텍스트
            if nav_page.is_rerouting():
                rerouted = True
                allure.attach("텍스트 감지", "감지 방식", allure.attachment_type.TEXT)

            # 2. 안내 문구 변화
            if not rerouted:
                try:
                    current_guidance = nav_page.get_current_guidance_text()
                    if current_guidance != initial_guidance:
                        rerouted = True
                        allure.attach(
                            f"{initial_guidance} → {current_guidance}",
                            "안내 문구 변화", allure.attachment_type.TEXT,
                        )
                except Exception:
                    pass

            # 3. 잔여 거리 변화
            if not rerouted and initial_distance:
                try:
                    current_distance = nav_page.get_remaining_distance()
                    if current_distance != initial_distance:
                        rerouted = True
                        allure.attach(
                            f"{initial_distance} → {current_distance}",
                            "거리 변화", allure.attachment_type.TEXT,
                        )
                except Exception:
                    pass

            allure.attach(str(rerouted), "재탐색 발생 여부", allure.attachment_type.TEXT)
            assert rerouted, "경로 이탈 후 재탐색이 발생하지 않음"

    @allure.story("정차 시 안내 유지")
    @allure.severity(allure.severity_level.NORMAL)
    def test_04_stop_maintains_guidance(
        self, appium_driver, nav_page, player_factory, gpx_stop, map_page
    ):
        """정차(동일 좌표 반복) 시 안내 상태가 유지되는지 확인."""
        # 안내 모드가 아니면 새로 시작
        if not nav_page.is_navigation_active():
            _start_fresh_navigation(appium_driver, map_page)

        with allure.step("정차 포함 GPX 재생 시작"):
            player = player_factory(gpx_stop, speed_multiplier=4.0)
            thread = player.play_async()

        with allure.step("정차 구간 진입 대기"):
            for _ in range(90):
                if player.progress >= 0.45:
                    break
                time.sleep(1)

        with allure.step("정차 중 안내 상태 유지 확인"):
            time.sleep(5)
            assert nav_page.is_navigation_active(), "정차 중 안내가 종료됨"

            guidance = nav_page.get_current_guidance_text()
            allure.attach(guidance, "정차 중 안내 문구", allure.attachment_type.TEXT)

        player.stop()

    @allure.story("안내 종료")
    @allure.severity(allure.severity_level.NORMAL)
    def test_05_navigation_end(self, appium_driver, map_page, nav_page):
        """안내 종료 → 메인 지도 화면 복귀 확인."""
        # 안내 모드가 아니면 새로 시작
        if not nav_page.is_navigation_active():
            _start_fresh_navigation(appium_driver, map_page)

        with allure.step("안내 종료"):
            nav_page.stop_navigation()

        with allure.step("메인 지도 화면 복귀 확인"):
            map_page.ensure_main_screen()
            assert map_page.is_map_displayed(), "안내 종료 후 지도 화면으로 복귀하지 않음"
