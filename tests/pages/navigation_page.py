"""티맵 경로 안내(주행) 화면 Page Object."""

import allure
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# ── 주행 안내 화면 셀렉터 ──────────────────────────────────────

# 잔여 거리 — CardView 내부의 distance_value만 선택 (TBT 거리와 구분)
REMAINING_DISTANCE_VALUE = (
    AppiumBy.XPATH,
    '//androidx.cardview.widget.CardView//android.widget.TextView[@resource-id="com.skt.tmap.ku:id/distance_value_text_view"]'
)
REMAINING_DISTANCE_UNIT = (
    AppiumBy.XPATH,
    '//androidx.cardview.widget.CardView//android.widget.TextView[@resource-id="com.skt.tmap.ku:id/distance_unit_text_view"]'
)

# 도착 예정 시간
ARRIVAL_TIME = (AppiumBy.ID, "com.skt.tmap.ku:id/time_text_view")
ARRIVAL_AMPM = (AppiumBy.ID, "com.skt.tmap.ku:id/am_pm_text_view")

# 안내 문구 (TBT 교차로명 등)
GUIDANCE_NAME = (
    AppiumBy.XPATH,
    '(//android.widget.TextView[@resource-id="com.skt.tmap.ku:id/name_text_view"])[1]'
)

# 현재 속도
CURRENT_SPEED = (AppiumBy.ID, "com.skt.tmap.ku:id/current_speed_text")

# 재탐색 버튼 (주행 중 항상 존재)
REROUTE_BUTTON = (AppiumBy.ID, "com.skt.tmap.ku:id/reroute_image_button_touch_area")

# 메뉴 버튼 (안내 종료 등)
MENU_BUTTON = (AppiumBy.ID, "com.skt.tmap.ku:id/menu_image_button_touch_area")

# 안내 종료 후 나타나는 주행종료 버튼
END_DRIVE_BUTTON = (AppiumBy.ID, "com.skt.tmap.ku:id/end_of_safe_drive_button")

# 주행 화면 고유 요소 (존재 여부로 안내 활성 판단)
DRIVING_VIEW = (AppiumBy.ID, "com.skt.tmap.ku:id/cv_driving_where_to_go")


class NavigationPage:
    """티맵 경로 안내(주행) 화면."""

    def __init__(self, driver) -> None:
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)

    def _find(self, locator, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(locator)
        )

    @allure.step("안내 화면 활성 여부 확인")
    def is_navigation_active(self) -> bool:
        """주행 안내 화면이 활성 상태인지 확인."""
        try:
            self._find(DRIVING_VIEW, timeout=5)
            return True
        except Exception:
            return False

    @allure.step("잔여 거리 확인")
    def get_remaining_distance(self) -> str:
        """잔여 거리 텍스트 반환 (예: '9.9km')."""
        value = self._find(REMAINING_DISTANCE_VALUE).text
        unit = self._find(REMAINING_DISTANCE_UNIT).text
        return f"{value}{unit}"

    @allure.step("도착 예정 시간 확인")
    def get_estimated_arrival_time(self) -> str:
        """도착 예정 시간 반환 (예: '오후 05:29')."""
        ampm = self._find(ARRIVAL_AMPM).text
        time_text = self._find(ARRIVAL_TIME).text
        return f"{ampm} {time_text}"

    @allure.step("현재 안내 문구 확인")
    def get_current_guidance_text(self) -> str:
        """현재 안내 문구 반환 (예: '교차로')."""
        return self._find(GUIDANCE_NAME).text

    @allure.step("현재 속도 확인")
    def get_current_speed(self) -> str:
        """현재 속도 텍스트 반환."""
        return self._find(CURRENT_SPEED).text

    @allure.step("재탐색 중 여부 확인")
    def is_rerouting(self) -> bool:
        """재탐색 관련 UI 변경 감지.

        경로 이탈 시 재탐색 텍스트 표시, 안내 문구 변경,
        또는 잔여 거리 급변으로 감지.
        """
        try:
            source = self.driver.page_source
            # 1. "재탐색" 또는 "경로이탈" 텍스트 존재
            if "재탐색" in source or "경로이탈" in source or "경로를 다시" in source:
                return True
            # 2. 안내 문구에 변경 징후 (다른 도로명 등)
            return False
        except Exception:
            return False

    def detect_reroute_by_distance_change(
        self, initial_distance: str, threshold_increase: bool = True
    ) -> bool:
        """잔여 거리 변화로 재탐색 감지.

        경로 이탈 후 재탐색 시 잔여 거리가 변경됨.
        """
        try:
            current = self.get_remaining_distance()
            return current != initial_distance
        except Exception:
            return False

    @allure.step("안내 종료")
    def stop_navigation(self) -> None:
        """메뉴 → 안내종료."""
        import time

        menu = self._find(MENU_BUTTON)
        menu.click()
        time.sleep(1)

        # 주행 메뉴의 "안내종료" 버튼
        end_btn = self._find(
            (AppiumBy.ID, "com.skt.tmap.ku:id/navi_drive_end"), timeout=5
        )
        end_btn.click()
        time.sleep(3)

    @allure.step("잔여 거리 변화 대기 (최대 {timeout}초)")
    def wait_for_distance_decrease(self, timeout: int = 30) -> bool:
        """잔여 거리 표시가 변경될 때까지 대기."""
        import time as _time
        try:
            initial = self.get_remaining_distance()
        except Exception:
            return False

        for _ in range(timeout):
            _time.sleep(1)
            try:
                current = self.get_remaining_distance()
                if current != initial:
                    return True
            except Exception:
                pass
        return False

    @allure.step("안내 갱신 대기 (최대 {timeout}초)")
    def wait_for_guidance_update(self, timeout: int = 30) -> bool:
        """안내 문구가 갱신될 때까지 대기."""
        import time as _time
        try:
            initial = self.get_current_guidance_text()
        except Exception:
            return False

        for _ in range(timeout):
            _time.sleep(1)
            try:
                current = self.get_current_guidance_text()
                if current != initial:
                    return True
            except Exception:
                pass
        return False
