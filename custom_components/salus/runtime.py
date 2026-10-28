"""Conservative, device-relay-based estimates of heating runtime.

A cloud snapshot cannot reconstruct exact transition timestamps or historic
runtime. Accumulate only between successful observations that are close enough
in time; never extrapolate through restarts or loss of cloud connectivity.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import math


class HeatingRuntime:
    """Shared accounting for legacy day/month runtime sensors of zone A."""

    MAX_GAP_SECONDS = 150  # default 60s scan + modest connection jitter

    def __init__(self) -> None:
        self.day: str | None = None
        self.month: str | None = None
        self.today_s = 0.0
        self.yesterday_s = 0.0
        self.month_s = 0.0
        self.previous_month_s = 0.0
        self._last_at: datetime | None = None
        self._last_active: bool | None = None
        self._restored = False

    @staticmethod
    def _month_key(dt: datetime) -> str:
        return dt.strftime("%Y-%m")

    def _roll(self, instant: datetime) -> None:
        new_day = instant.date().isoformat()
        new_month = self._month_key(instant)
        if self.day is None:
            self.day = new_day
        elif self.day != new_day:
            old_day = datetime.fromisoformat(self.day).date()
            # There can be missed days; do not label old runtime as yesterday.
            self.yesterday_s = self.today_s if instant.date() - old_day == timedelta(days=1) else 0.0
            self.today_s = 0.0
            self.day = new_day
        if self.month is None:
            self.month = new_month
        elif self.month != new_month:
            previous = (instant.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
            self.previous_month_s = self.month_s if self.month == previous else 0.0
            self.month_s = 0.0
            self.month = new_month

    def observe(self, instant: datetime, heating: bool | None) -> None:
        """Account for a bounded preceding interval, then record new relay state."""
        if instant.tzinfo is None:
            raise ValueError("HeatingRuntime expects timezone-aware observation timestamps")
        if self._last_at is not None and instant > self._last_at and self._last_active is True:
            elapsed = (instant - self._last_at).total_seconds()
            if 0 < elapsed <= self.MAX_GAP_SECONDS:
                cursor = self._last_at
                while cursor < instant:
                    # Calculate calendar boundaries in the original local timezone.
                    next_day = (cursor + timedelta(days=1)).date()
                    boundary = datetime.combine(next_day, datetime.min.time(), tzinfo=cursor.tzinfo)
                    end = min(instant, boundary)
                    if end <= cursor:  # Guard unusual DST/timezone transitions.
                        break
                    self._roll(cursor)
                    period_s = (end - cursor).total_seconds()
                    self.today_s += period_s
                    self.month_s += period_s
                    cursor = end
        self._roll(instant)
        self._last_at = instant
        self._last_active = heating

    def read_hours(self, kind: str) -> float:
        return round({
            "today": self.today_s,
            "yesterday": self.yesterday_s,
            "month": self.month_s,
            "previous_month": self.previous_month_s,
            "heating_time": self.today_s,
        }[kind] / 3600, 3)

    def snapshot(self) -> dict:
        return {
            "runtime_day": self.day,
            "runtime_month": self.month,
            "runtime_today_s": round(self.today_s, 3),
            "runtime_yesterday_s": round(self.yesterday_s, 3),
            "runtime_month_s": round(self.month_s, 3),
            "runtime_previous_month_s": round(self.previous_month_s, 3),
            "runtime_method": "estimated from sampled A87 heating relay; incomplete cloud gaps excluded",
        }

    def restore(self, attrs: dict, now: datetime) -> bool:
        """Restore only new-format snapshots; never treat old flawed totals as truth."""
        if self._restored:
            return False
        self._restored = True
        fields = ("runtime_today_s", "runtime_yesterday_s", "runtime_month_s", "runtime_previous_month_s")
        if not isinstance(attrs, dict) or not all(x in attrs for x in fields):
            self._last_at = None
            return False
        try:
            values = [float(attrs[x]) for x in fields]
            day, month = attrs["runtime_day"], attrs["runtime_month"]
            if (not all(math.isfinite(x) and x >= 0 for x in values)
                    or datetime.fromisoformat(day).date().isoformat() != day
                    or len(month) != 7):
                return False
        except (ValueError, TypeError, KeyError, AttributeError):
            return False
        self.day, self.month = day, month
        (self.today_s, self.yesterday_s, self.month_s, self.previous_month_s) = values
        self._roll(now)
        self._last_at = now
        return True
