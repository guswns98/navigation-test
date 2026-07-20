"""티맵 메인 지도 화면 Page Object."""

import time

import allure
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# ── 실제 티맵 UI 셀렉터 (UI Automator 덤프 기반) ──────────────

# 메인 화면
SEARCH_BAR = (AppiumBy.ID, "com.skt.tmap.ku:id/tmap_main_search_bar_layout")
SEARCH_BAR_TEXT = (AppiumBy.ID, "com.skt.tmap.ku:id/tmap_main_search_bar_textview")

# 검색 화면
SEARCH_INPUT = (AppiumBy.ID, "com.skt.tmap.ku:id/search_edit_text")
FIRST_ROUTE_BUTTON = (AppiumBy.XPATH, '(//android.widget.Button[@text="길찾기"])[1]')

# 경로 미리보기 화면
START_GUIDANCE = (AppiumBy.ID, "com.skt.tmap.ku:id/route_preview_drive_button")


class MapPage:
    """티맵 메인 지도 화면."""

    def __init__(self, driver) -> None:
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)

    def _find(self, locator, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(locator)
        )

    def ensure_main_screen(self) -> None:
        """메인 화면이 아니면 뒤로가기로 복귀."""
        for _ in range(5):
            try:
                self.driver.find_element(*SEARCH_BAR)
                return
            except Exception:
                self.driver.press_keycode(4)
                time.sleep(1)

    @allure.step("목적지 검색: {query}")
    def search_destination(self, query: str) -> None:
        """검색창 탭 → 검색어 입력 → 검색 실행."""
        search_bar = self._find(SEARCH_BAR)
        search_bar.click()
        time.sleep(1)

        search_input = self._find(SEARCH_INPUT)
        search_input.clear()
        search_input.send_keys(query)
        self.driver.press_keycode(66)  # Enter
        time.sleep(3)

    @allure.step("첫 번째 검색 결과 길찾기")
    def select_first_result(self) -> None:
        """검색 결과 목록에서 첫 번째 '길찾기' 버튼 탭."""
        route_btn = self._find(FIRST_ROUTE_BUTTON)
        route_btn.click()
        time.sleep(5)

    @allure.step("안내 시작")
    def start_navigation(self) -> None:
        """경로 미리보기 화면에서 안내시작 버튼 탭."""
        start_btn = self._find(START_GUIDANCE)
        start_btn.click()
        time.sleep(5)

    @allure.step("지도 표시 여부 확인")
    def is_map_displayed(self) -> bool:
        """메인 지도 화면이 표시되는지 확인."""
        try:
            self._find(SEARCH_BAR, timeout=5)
            return True
        except Exception:
            return False

    @allure.step("현재 위치 텍스트 확인")
    def get_current_location_text(self) -> str:
        """검색바 텍스트 반환."""
        try:
            el = self._find(SEARCH_BAR_TEXT, timeout=5)
            return el.text
        except Exception:
            return ""
