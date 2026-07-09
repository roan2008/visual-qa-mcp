from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ChartLayout:
    width: int = 700
    height: int = 500
    margin_left: int = 130
    margin_right: int = 40
    margin_top: int = 84
    margin_bottom: int = 110
    axis_label_box: tuple[int, int, int, int] = (170, 26, 610, 58)
    x_label_offset_y: int = 28
    label_box_width: int = 104
    label_box_height: int = 26
    tick_label_width: int = 84
    tick_label_height: int = 22

    @property
    def plot_left(self) -> int:
        return self.margin_left

    @property
    def plot_top(self) -> int:
        return self.margin_top

    @property
    def plot_right(self) -> int:
        return self.width - self.margin_right

    @property
    def plot_bottom(self) -> int:
        return self.height - self.margin_bottom

    @property
    def plot_width(self) -> int:
        return self.plot_right - self.plot_left

    @property
    def plot_height(self) -> int:
        return self.plot_bottom - self.plot_top

    def with_overrides(self, **overrides: int | tuple[int, int, int, int]) -> "ChartLayout":
        return replace(self, **overrides)

    def bar_slot_width(self, bar_count: int) -> float:
        return self.plot_width / max(bar_count, 1)

    def value_to_y(self, value: float, axis_min: float, axis_max: float) -> int:
        if axis_max == axis_min:
            return self.plot_bottom
        ratio = (value - axis_min) / (axis_max - axis_min)
        return round(self.plot_bottom - ratio * self.plot_height)

    def bar_box(
        self,
        bar_index: int,
        bar_count: int,
        value: float,
        axis_min: float,
        axis_max: float,
        baseline_value: float,
    ) -> list[int]:
        slot_width = self.bar_slot_width(bar_count)
        left = int(self.plot_left + bar_index * slot_width + slot_width * 0.2)
        right = int(self.plot_left + (bar_index + 1) * slot_width - slot_width * 0.2)
        baseline_y = self.value_to_y(baseline_value, axis_min, axis_max)
        value_y = self.value_to_y(value, axis_min, axis_max)
        top = min(baseline_y, value_y)
        bottom = max(baseline_y, value_y)
        return [left, top, right, bottom]

    def label_box(self, center_x: int) -> list[int]:
        left = center_x - self.label_box_width // 2
        top = self.plot_bottom + self.x_label_offset_y
        return [left, top, left + self.label_box_width, top + self.label_box_height]

    def tick_label_box(self, tick_y: int) -> list[int]:
        left = max(0, self.plot_left - self.tick_label_width - 14)
        top = tick_y - self.tick_label_height // 2
        return [left, top, left + self.tick_label_width, top + self.tick_label_height]
