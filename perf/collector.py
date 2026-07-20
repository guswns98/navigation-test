"""비기능 성능 지표 수집 모듈.

adb를 통해 티맵 앱의 콜드 스타트 시간, 메모리 사용량, 프레임 통계를 수집합니다.
"""

import re
import subprocess
import time
from dataclasses import dataclass

APP_PACKAGE = "com.skt.tmap.ku"
APP_ACTIVITY = "com.skt.tmap.activity.TmapIntroActivity"


def _adb(args: list[str]) -> str:
    """adb 명령 실행 후 stdout 반환."""
    result = subprocess.run(
        ["adb", *args],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


@dataclass
class ColdStartResult:
    """콜드 스타트 측정 결과."""
    total_time_ms: int
    wait_time_ms: int
    raw_output: str


@dataclass
class MemoryResult:
    """메모리 사용량 측정 결과."""
    total_pss_kb: int
    java_heap_kb: int
    native_heap_kb: int
    raw_output: str


@dataclass
class FrameResult:
    """프레임 통계 측정 결과."""
    total_frames: int
    janky_frames: int
    janky_percent: float
    percentile_90_ms: float
    percentile_95_ms: float
    percentile_99_ms: float
    raw_output: str


def measure_cold_start(repeat: int = 3) -> list[ColdStartResult]:
    """콜드 스타트 시간 측정.

    앱을 강제 종료 후 am start -W로 시작하여 TotalTime을 측정합니다.

    Args:
        repeat: 반복 측정 횟수.

    Returns:
        ColdStartResult 리스트.
    """
    results: list[ColdStartResult] = []

    for _ in range(repeat):
        # 앱 강제 종료 + 캐시 정리
        _adb(["shell", "am", "force-stop", APP_PACKAGE])
        time.sleep(2)

        # 콜드 스타트
        output = _adb([
            "shell", "am", "start", "-W",
            "-n", f"{APP_PACKAGE}/{APP_ACTIVITY}",
        ])

        total_time = 0
        wait_time = 0
        for line in output.splitlines():
            if "TotalTime:" in line:
                total_time = int(re.search(r"(\d+)", line).group(1))
            if "WaitTime:" in line:
                wait_time = int(re.search(r"(\d+)", line).group(1))

        results.append(ColdStartResult(
            total_time_ms=total_time,
            wait_time_ms=wait_time,
            raw_output=output.strip(),
        ))

        time.sleep(3)  # 앱 완전 로딩 대기

    return results


def measure_memory() -> MemoryResult:
    """메모리 사용량 측정 (dumpsys meminfo)."""
    output = _adb(["shell", "dumpsys", "meminfo", APP_PACKAGE])

    total_pss = 0
    java_heap = 0
    native_heap = 0

    for line in output.splitlines():
        line = line.strip()
        if line.startswith("TOTAL PSS:") or line.startswith("TOTAL:"):
            match = re.search(r"(\d[\d,]*)", line)
            if match:
                total_pss = int(match.group(1).replace(",", ""))
        elif "Java Heap:" in line:
            match = re.search(r"(\d[\d,]*)", line)
            if match:
                java_heap = int(match.group(1).replace(",", ""))
        elif "Native Heap:" in line:
            match = re.search(r"(\d[\d,]*)", line)
            if match:
                native_heap = int(match.group(1).replace(",", ""))

    # TOTAL 행에서 추출 (대안)
    if total_pss == 0:
        for line in output.splitlines():
            if "TOTAL" in line and "TOTAL PSS" not in line:
                numbers = re.findall(r"\d[\d,]*", line)
                if numbers:
                    total_pss = int(numbers[0].replace(",", ""))
                    break

    return MemoryResult(
        total_pss_kb=total_pss,
        java_heap_kb=java_heap,
        native_heap_kb=native_heap,
        raw_output=output.strip(),
    )


def measure_frames(duration_seconds: int = 10) -> FrameResult:
    """프레임 통계 측정 (dumpsys gfxinfo).

    gfxinfo를 리셋한 뒤 일정 시간 대기 후 수집합니다.

    Args:
        duration_seconds: 프레임 수집 대기 시간 (초).
    """
    # 프레임 통계 리셋
    _adb(["shell", "dumpsys", "gfxinfo", APP_PACKAGE, "reset"])
    time.sleep(duration_seconds)

    output = _adb(["shell", "dumpsys", "gfxinfo", APP_PACKAGE])

    total_frames = 0
    janky_frames = 0
    janky_percent = 0.0
    p90 = 0.0
    p95 = 0.0
    p99 = 0.0

    for line in output.splitlines():
        line = line.strip()
        if "Total frames rendered:" in line:
            match = re.search(r"(\d+)", line)
            if match:
                total_frames = int(match.group(1))
        elif "Janky frames:" in line:
            match = re.search(r"(\d+)\s*\(([\d.]+)%\)", line)
            if match:
                janky_frames = int(match.group(1))
                janky_percent = float(match.group(2))
        elif "90th percentile:" in line:
            match = re.search(r"(\d+)", line)
            if match:
                p90 = float(match.group(1))
        elif "95th percentile:" in line:
            match = re.search(r"(\d+)", line)
            if match:
                p95 = float(match.group(1))
        elif "99th percentile:" in line:
            match = re.search(r"(\d+)", line)
            if match:
                p99 = float(match.group(1))

    return FrameResult(
        total_frames=total_frames,
        janky_frames=janky_frames,
        janky_percent=janky_percent,
        percentile_90_ms=p90,
        percentile_95_ms=p95,
        percentile_99_ms=p99,
        raw_output=output.strip(),
    )
