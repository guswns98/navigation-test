"""티맵 메인 지도 화면 Page Object."""

import allure
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# UI 셀렉터 상수 (앱 버전에 따라 변경 필요)
# accessibility id 우선, xpath는 최후 수단
SEARCH_BOX = (AppiumBy.ACCESSIBILITY_ID, "search_box")
SEARCH_INPUT = (AppiumBy.ACCESSIBILITY_ID, "search_input")
FIRST_RESULT = (AppiumBy.ACCESSIBILITY_ID, "search_result_0")
NAVIGATE_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "btn_navigate")
START_GUIDANCE_BUTTON = (AppiumBy.ACCESSIBILITY_ID, "btn_start_guidance")
MAP_VIEW = (AppiumBy.ACCESSIBILITY_ID, "map_view")

# xpath 폴백 — 앱 업데이트 시 깨질 수 있음
SEARCH_BOX_XPATH = (AppiumBy.XPATH, '//android.widget.EditText[contains(@text, "검색")]')
NAVIGATE_BUTTON_XPATH = (AppiumBy.XPATH, '//android.widget.Button[contains(@text, "안내")]')
START_GUIDANCE_XPATH = (AppiumBy.XPATH, '//android.widget.Button[contains(@text, "안내시작")]')


class MapPage:
    """티맵 메인 지도 화면."""

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

    @allure.step("목적지 검색: {query}")
    def search_destination(self, query: str) -> None:
        """검색창에 목적지를 입력."""
        search = self._find(SEARCH_BOX, SEARCH_BOX_XPATH)
        search.click()

        search_input = self._find(SEARCH_INPUT)
        search_input.clear()
        search_input.send_keys(query)

        # 검색 실행 (엔터 키)
        self.driver.press_keycode(66)

    @allure.step("첫 번째 검색 결과 선택")
    def select_first_result(self) -> None:
        """검색 결과 목록에서 첫 번째 항목 선택."""
        result = self._find(FIRST_RESULT)
        result.click()

    @allure.step("경로 안내 시작")
    def start_navigation(self) -> None:
        """길안내 버튼 → 안내시작 버튼 순서로 탭."""
        nav_btn = self._find(NAVIGATE_BUTTON, NAVIGATE_BUTTON_XPATH)
        nav_btn.click()

        start_btn = self._find(START_GUIDANCE_BUTTON, START_GUIDANCE_XPATH)
        start_btn.click()

    @allure.step("지도 표시 여부 확인")
    def is_map_displayed(self) -> bool:
        """메인 지도 뷰가 화면에 표시되는지 확인."""
        try:
            self._find(MAP_VIEW, timeout=5)
            return True
        except Exception:
            return False

    @allure.step("현재 위치 텍스트 확인")
    def get_current_location_text(self) -> str:
        """현재 위치 표시 텍스트 반환."""
        try:
            el = self.driver.find_element(
                AppiumBy.ACCESSIBILITY_ID, "current_location_text"
            )
            return el.text
        except Exception:
            return ""
