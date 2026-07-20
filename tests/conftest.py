"""pytest 공통 fixture — Appium 세션, GPX Player, Allure 스크린샷."""

import os

import allure
import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options

from gpx_player.player import AdbBackend, GpxPlayer


# ── Appium 설정 ──────────────────────────────────────────────

APPIUM_HOST = os.getenv("APPIUM_HOST", "http://127.0.0.1:4723")

DEFAULT_CAPS = {
    "platformName": "Android",
    "automationName": "UiAutomator2",
    "appPackage": "com.skt.tmap.ku",
    "appActivity": "com.skt.tmap.activity.TmapSplashActivity",
    "noReset": True,           # 로그인 상태 유지
    "autoGrantPermissions": True,
    "newCommandTimeout": 300,
}


# ── Fixtures ─────────────────────────────────────────────────

@pytest.fixture(scope="session")
def appium_driver():
    """Appium 세션을 생성하고 테스트 종료 시 정리."""
    options = UiAutomator2Options()
    for key, value in DEFAULT_CAPS.items():
        options.set_capability(key, value)

    # 환경 변수로 추가 capability 오버라이드
    if device_name := os.getenv("DEVICE_NAME"):
        options.set_capability("deviceName", device_name)
    if avd_name := os.getenv("AVD_NAME"):
        options.set_capability("avd", avd_name)

    driver = webdriver.Remote(APPIUM_HOST, options=options)
    driver.implicitly_wait(10)

    yield driver

    driver.quit()


@pytest.fixture
def adb_backend() -> AdbBackend:
    """ADB 기반 좌표 주입 백엔드."""
    return AdbBackend()


@pytest.fixture
def player_factory(adb_backend):
    """GPX Player 팩토리 — gpx_path를 인자로 받아 Player 생성.

    사용: player = player_factory("route.gpx", speed_multiplier=2.0)
    """
    players: list[GpxPlayer] = []

    def _create(gpx_path: str, speed_multiplier: float = 2.0) -> GpxPlayer:
        player = GpxPlayer(gpx_path, adb_backend, speed_multiplier=speed_multiplier)
        players.append(player)
        return player

    yield _create

    # 테스트 종료 시 모든 플레이어 정지
    for p in players:
        p.stop()


# ── Allure: 실패 시 스크린샷 첨부 ─────────────────────────────

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """테스트 실패 시 Appium 스크린샷을 Allure 리포트에 첨부."""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        driver = item.funcargs.get("appium_driver")
        if driver:
            try:
                screenshot = driver.get_screenshot_as_png()
                allure.attach(
                    screenshot,
                    name="failure_screenshot",
                    attachment_type=allure.attachment_type.PNG,
                )
            except Exception:
                pass  # 스크린샷 실패는 무시
