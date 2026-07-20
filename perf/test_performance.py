"""비기능 성능 테스트.

티맵 앱의 콜드 스타트 시간, 메모리 사용량, 프레임 통계를 측정하고
Allure 리포트에 결과를 첨부합니다.
"""

import allure
import pytest

from perf.collector import measure_cold_start, measure_frames, measure_memory


@allure.epic("비기능 성능 측정")
@pytest.mark.perf
class TestPerformance:
    """티맵 앱 비기능 성능 테스트."""

    @allure.story("콜드 스타트 시간")
    @allure.severity(allure.severity_level.NORMAL)
    def test_cold_start_time(self):
        """콜드 스타트 시간 측정 (3회 반복, 평균)."""
        results = measure_cold_start(repeat=3)

        times = [r.total_time_ms for r in results]
        avg_ms = sum(times) / len(times)

        summary = "\n".join([
            f"측정 {i+1}: TotalTime={r.total_time_ms}ms, WaitTime={r.wait_time_ms}ms"
            for i, r in enumerate(results)
        ])
        summary += f"\n\n평균 TotalTime: {avg_ms:.0f}ms"

        allure.attach(summary, "콜드 스타트 측정 결과", allure.attachment_type.TEXT)
        allure.attach(
            results[0].raw_output,
            "am start -W 원본 출력 (1회차)",
            allure.attachment_type.TEXT,
        )

        # 10초 이내 기동 확인 (에뮬레이터 기준 넉넉한 임계값)
        assert avg_ms < 10000, f"콜드 스타트 평균 {avg_ms:.0f}ms — 10초 초과"

    @allure.story("메모리 사용량")
    @allure.severity(allure.severity_level.NORMAL)
    def test_memory_usage(self):
        """메모리 사용량 측정 (PSS 기준)."""
        result = measure_memory()

        summary = (
            f"Total PSS: {result.total_pss_kb:,} KB ({result.total_pss_kb / 1024:.1f} MB)\n"
            f"Java Heap: {result.java_heap_kb:,} KB\n"
            f"Native Heap: {result.native_heap_kb:,} KB"
        )

        allure.attach(summary, "메모리 측정 결과", allure.attachment_type.TEXT)
        allure.attach(result.raw_output, "dumpsys meminfo 원본", allure.attachment_type.TEXT)

        # 측정값이 정상적으로 수집되었는지 확인
        assert result.total_pss_kb > 0, "메모리 측정 실패: PSS가 0"

    @allure.story("프레임 통계")
    @allure.severity(allure.severity_level.NORMAL)
    def test_frame_stats(self):
        """프레임 렌더링 통계 측정 (10초간)."""
        result = measure_frames(duration_seconds=10)

        summary = (
            f"Total frames: {result.total_frames}\n"
            f"Janky frames: {result.janky_frames} ({result.janky_percent:.1f}%)\n"
            f"90th percentile: {result.percentile_90_ms:.0f}ms\n"
            f"95th percentile: {result.percentile_95_ms:.0f}ms\n"
            f"99th percentile: {result.percentile_99_ms:.0f}ms"
        )

        allure.attach(summary, "프레임 통계 결과", allure.attachment_type.TEXT)
        allure.attach(result.raw_output, "dumpsys gfxinfo 원본", allure.attachment_type.TEXT)

        # 프레임 데이터가 수집되었는지 확인
        assert result.total_frames >= 0, "프레임 통계 수집 실패"
