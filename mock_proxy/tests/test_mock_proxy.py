"""Mock Proxy 장애 주입 검증 테스트.

mitmproxy를 프록시 서버로 기동한 뒤, 데모 클라이언트를 통해
rules.yaml의 각 장애 시나리오가 올바르게 동작하는지 검증합니다.

실행:
    pytest mock_proxy/tests/test_mock_proxy.py -v
"""

import shutil
import subprocess
import time
from pathlib import Path

import allure
import pytest
import yaml

from mock_proxy.demo_client import RouteClient, RouteClientError

PROXY_PORT = 8080
PROXY_URL = f"http://127.0.0.1:{PROXY_PORT}"
RULES_PATH = Path(__file__).parent.parent / "rules.yaml"
RULES_BACKUP = RULES_PATH.with_suffix(".yaml.bak")

ORIGIN = (37.5665, 126.9780)
DESTINATION = (37.4979, 127.0276)


@pytest.fixture(scope="module")
def proxy_server():
    """mitmproxy 서버를 백그라운드로 기동."""
    mitmdump = shutil.which("mitmdump")
    if not mitmdump:
        pytest.skip("mitmdump이 설치되어 있지 않음")

    proc = subprocess.Popen(
        [mitmdump, "-s", str(Path(__file__).parent.parent / "proxy.py"),
         "-p", str(PROXY_PORT), "--set", "flow_detail=0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(3)  # 서버 기동 대기

    yield proc

    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture(autouse=True)
def reset_rules():
    """각 테스트 전후로 rules.yaml을 초기 상태로 복원."""
    # 원본 백업
    shutil.copy(RULES_PATH, RULES_BACKUP)
    yield
    # 복원
    shutil.copy(RULES_BACKUP, RULES_PATH)
    RULES_BACKUP.unlink(missing_ok=True)


def _enable_rule(rule_name: str) -> None:
    """rules.yaml에서 특정 규칙을 활성화."""
    with open(RULES_PATH) as f:
        data = yaml.safe_load(f)

    for rule in data.get("rules", []):
        rule["enabled"] = rule["name"] == rule_name

    with open(RULES_PATH, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


@allure.epic("API Mocking 도구")
@allure.feature("장애 주입 검증")
@pytest.mark.mock_proxy
class TestMockProxy:
    """Mock Proxy 장애 시나리오 테스트."""

    @allure.story("정상 응답")
    def test_normal_response(self, proxy_server):
        """프록시 경유 시 규칙 비활성 상태에서 정상 응답 확인."""
        client = RouteClient(proxy=PROXY_URL, timeout=10)
        result = client.get_route(ORIGIN, DESTINATION)

        assert result["code"] == "Ok"
        assert len(result["routes"]) > 0
        assert result["routes"][0]["geometry"]["coordinates"]

    @allure.story("500 에러 응답")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_server_error_500(self, proxy_server):
        """server_error 규칙 활성화 시 500 응답 + 클라이언트 에러 처리 확인."""
        _enable_rule("server_error")
        time.sleep(1)  # 핫리로드 대기

        client = RouteClient(proxy=PROXY_URL, timeout=10)

        with pytest.raises(RouteClientError, match="HTTP 500"):
            client.get_route(ORIGIN, DESTINATION)

    @allure.story("지연 응답 → 타임아웃")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_slow_response_timeout(self, proxy_server):
        """slow_response 규칙(3초 지연) 활성화 시 타임아웃 처리 확인."""
        _enable_rule("slow_response")
        time.sleep(1)

        # 타임아웃을 2초로 설정 → 3초 지연이므로 타임아웃 발생
        client = RouteClient(proxy=PROXY_URL, timeout=2)

        with pytest.raises(RouteClientError, match="타임아웃"):
            client.get_route(ORIGIN, DESTINATION)

    @allure.story("빈 경로 응답")
    @allure.severity(allure.severity_level.NORMAL)
    def test_empty_route_response(self, proxy_server):
        """empty_route 규칙 활성화 시 빈 경로 에러 처리 확인."""
        _enable_rule("empty_route")
        time.sleep(1)

        client = RouteClient(proxy=PROXY_URL, timeout=10)

        with pytest.raises(RouteClientError, match="경로 없음"):
            client.get_route(ORIGIN, DESTINATION)

    @allure.story("손상된 JSON 응답")
    @allure.severity(allure.severity_level.NORMAL)
    def test_malformed_json_response(self, proxy_server):
        """malformed_json 규칙 활성화 시 데이터 손상 에러 처리 확인."""
        _enable_rule("malformed_json")
        time.sleep(1)

        client = RouteClient(proxy=PROXY_URL, timeout=10)

        with pytest.raises(RouteClientError, match="geometry가 null|API 에러"):
            client.get_route(ORIGIN, DESTINATION)
