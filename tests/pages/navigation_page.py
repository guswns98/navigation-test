"""티맵 경로 안내 화면 Page Object."""

import allure
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# UI 셀렉터 상수 (앱 버전에 따라 변경 필요)
GUIDANCE_VIEW = (AppiumBy.ACCESSIBILITY_ID, "guidance_view")
REMAINING_DISTANCE = (AppiumBy.ACCESSIBILITY_ID, "remaining_distance")
ESTIMATED_ARRIVAL = (AppiumBy.ACCESSIBILITY_ID, "estimated_arrival_time")
GUIDANCE_TEXT = (AppiumBy.ACCESSIBILITY_ID, "guidance_text")
REROUTE_INDICATOR = (AppiumBy.ACCESSIBILITY_ID, "reroute_indicator")
STOP_NAVIGATION = (AppiumBy.ACCESSIBILITY_ID, "btn_stop_navigation")

# xpath 폴백
REMAINING_DISTANCE_XPATH = (
    AppiumBy.XPATH, '//android.widget.TextView[contains(@resource-id, "distance")]'
)
GUIDANCE_TEXT_XPATH = (
    AppiumBy.XPATH, '//android.widget.TextView[contains(@resource-id, "guidance")]'
)
REROUTE_TEXT_XPATH = (
    AppiumBy.XPATH, '//android.widget.TextView[contains(@text, "재탐색")]'
)
STOP_NAV_XPATH = (
    AppiumBy.XPATH, '//android.widget.Button[contains(@text, "종료")]'
)


class NavigationPage:
    """티맵 경로 안내 화면."""

    def __init__(self, driver) -> None:
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)

    def _find(self, primary, fallback=None, timeout=10):
        """accessibility id로 먼저 시도, 실패하면 xpath 폴백."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(primary)
            )
        except Exception:
            if fallback:
                return WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located(fallback)
                )
            raise

    @allure.step("안내 화면 활성 여부 확인")
    def is_navigation_active(self) -> bool:
        """경로 안내 화면이 활성 상태인지 확인."""
        try:
            self._find(GUIDANCE_VIEW, timeout=5)
            return True
        except Exception:
            return False

    @allure.step("잔여 거리 확인")
    def get_remaining_distance(self) -> str:
        """잔여 거리 텍스트 반환 (예: '3.2km')."""
        el = self._find(REMAINING_DISTANCE, REMAINING_DISTANCE_XPATH)
        return el.text

    @allure.step("도착 예정 시간 확인")
    def get_estimated_arrival_time(self) -> str:
        """도착 예정 시간 텍스트 반환."""
        el = self._find(ESTIMATED_ARRIVAL)
        return el.text

    @allure.step("현재 안내 문구 확인")
    def get_current_guidance_text(self) -> str:
        """현재 안내 문구 반환 (예: '300m 앞 우회전')."""
        el = self._find(GUIDANCE_TEXT, GUIDANCE_TEXT_XPATH)
        return el.text

    @allure.step("재탐색 중 여부 확인")
    def is_rerouting(self) -> bool:
        """재탐색 표시가 화면에 있는지 확인."""
        try:
            self._find(REROUTE_INDICATOR, REROUTE_TEXT_XPATH, timeout=5)
            return True
        except Exception:
            return False

    @allure.step("안내 종료")
    def stop_navigation(self) -> None:
        """경로 안내 종료 버튼 탭."""
        btn = self._find(STOP_NAVIGATION, STOP_NAV_XPATH)
        btn.click()

    @allure.step("안내 갱신 대기 (최대 {timeout}초)")
    def wait_for_guidance_update(self, timeout: int = 30) -> bool:
        """안내 문구가 갱신될 때까지 대기.

        Returns:
            갱신 감지 시 True, 타임아웃 시 False.
        """
        try:
            initial_text = self.get_current_guidance_text()
        except Exception:
            return False

        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: self.get_current_guidance_text() != initial_text
            )
            return True
        except Exception:
            return False

    @allure.step("잔여 거리 감소 대기 (최대 {timeout}초)")
    def wait_for_distance_decrease(self, timeout: int = 30) -> bool:
        """잔여 거리 표시가 변경될 때까지 대기."""
        try:
            initial = self.get_remaining_distance()
        except Exception:
            return False

        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: self.get_remaining_distance() != initial
            )
            return True
        except Exception:
            return False
