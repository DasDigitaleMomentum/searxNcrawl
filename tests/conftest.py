"""Global pytest hooks for strict test-accounting guardrails."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _TestAccounting:
    deselected: int = 0
    skipped: int = 0
    xfailed: int = 0
    xpassed: int = 0


_ACCOUNTING = _TestAccounting()


def pytest_deselected(items):  # pragma: no cover - pytest hook
    _ACCOUNTING.deselected += len(items)


def pytest_runtest_logreport(report):  # pragma: no cover - pytest hook
    if report.when not in {"setup", "call"}:
        return

    is_xfail = bool(getattr(report, "wasxfail", False))
    if is_xfail:
        if report.outcome == "skipped":
            _ACCOUNTING.xfailed += 1
        elif report.outcome == "passed":
            _ACCOUNTING.xpassed += 1
        return

    if report.outcome == "skipped":
        _ACCOUNTING.skipped += 1


def pytest_sessionfinish(session, exitstatus):  # pragma: no cover - pytest hook
    violations = []
    if _ACCOUNTING.deselected:
        violations.append(f"deselected={_ACCOUNTING.deselected}")
    if _ACCOUNTING.skipped:
        violations.append(f"skipped={_ACCOUNTING.skipped}")
    if _ACCOUNTING.xfailed:
        violations.append(f"xfailed={_ACCOUNTING.xfailed}")
    if _ACCOUNTING.xpassed:
        violations.append(f"xpassed={_ACCOUNTING.xpassed}")

    if not violations:
        return

    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter:
        reporter.write_sep(
            "=",
            "Strict guard failed: test accounting violations detected "
            f"({', '.join(violations)})",
        )
        reporter.write_line(
            "Hard guard requires zero skipped/deselected/xfail/xpass tests."
        )

    session.exitstatus = 1
