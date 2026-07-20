"""mitmproxy 애드온: rules.yaml 기반 선언적 장애 주입 프록시.

사용법:
    mitmdump -s mock_proxy/proxy.py

규칙 파일은 mock_proxy/rules.yaml을 기본으로 로드하며,
파일 변경 시 자동으로 핫리로드됩니다.
"""

import json
import time
from fnmatch import fnmatch
from pathlib import Path

import yaml
from mitmproxy import http

RULES_PATH = Path(__file__).parent / "rules.yaml"


class MockProxyAddon:
    """선언적 규칙 기반 API 응답 변조 애드온."""

    def __init__(self, rules_path: Path = RULES_PATH):
        self.rules_path = rules_path
        self._rules: list[dict] = []
        self._last_mtime: float = 0.0
        self._load_rules()

    def _load_rules(self) -> None:
        """규칙 파일 로드."""
        try:
            mtime = self.rules_path.stat().st_mtime
            if mtime == self._last_mtime:
                return
            self._last_mtime = mtime

            with open(self.rules_path) as f:
                data = yaml.safe_load(f)
            self._rules = data.get("rules", [])
        except Exception as e:
            print(f"[MockProxy] 규칙 로드 실패: {e}")

    def _find_matching_rule(self, path: str) -> dict | None:
        """요청 경로에 매칭되는 활성 규칙 반환."""
        self._load_rules()  # 핫리로드 체크
        for rule in self._rules:
            if not rule.get("enabled", False):
                continue
            pattern = rule.get("endpoint", "")
            if fnmatch(path, pattern):
                return rule
        return None

    def response(self, flow: http.HTTPFlow) -> None:
        """응답 가로채기 - 매칭 규칙에 따라 변조."""
        rule = self._find_matching_rule(flow.request.path)
        if rule is None:
            return

        action = rule.get("action", {})
        action_type = action.get("type")
        name = rule.get("name", "unknown")

        if action_type == "status_code":
            flow.response.status_code = action["value"]
            if "body" in action:
                flow.response.text = action["body"]
            print(f"[MockProxy] '{name}' 적용: status={action['value']}")

        elif action_type == "delay":
            seconds = action.get("seconds", 1)
            time.sleep(seconds)
            print(f"[MockProxy] '{name}' 적용: {seconds}초 지연")

        elif action_type == "modify_body":
            flow.response.text = action["body"]
            flow.response.headers["content-type"] = "application/json"
            print(f"[MockProxy] '{name}' 적용: 응답 바디 변조")


addons = [MockProxyAddon()]
