from __future__ import annotations

import numpy as np


def connected_components(mask: np.ndarray) -> list[np.ndarray]:
    """Return arrays of (y, x) coordinates using deterministic 8-connectivity.

    Run-length union-find keeps Python work proportional to horizontal runs
    rather than foreground pixels. This preserves the original component
    contract while avoiding repeated per-pixel flood fills on large regions.
    """
    parent: list[int] = []
    runs: list[tuple[int, int, int, int]] = []
    previous: list[tuple[int, int, int]] = []

    def find(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    for y in range(mask.shape[0]):
        xs = np.flatnonzero(mask[y])
        current: list[tuple[int, int, int]] = []
        if len(xs):
            split_at = np.flatnonzero(np.diff(xs) > 1) + 1
            for segment in np.split(xs, split_at):
                x0, x1 = int(segment[0]), int(segment[-1])
                label = len(parent)
                parent.append(label)
                for prev_x0, prev_x1, prev_label in previous:
                    if prev_x1 < x0 - 1:
                        continue
                    if prev_x0 > x1 + 1:
                        break
                    union(label, prev_label)
                runs.append((y, x0, x1, label))
                current.append((x0, x1, label))
        previous = current

    grouped: dict[int, list[tuple[int, int, int]]] = {}
    for y, x0, x1, label in runs:
        grouped.setdefault(find(label), []).append((y, x0, x1))

    components: list[np.ndarray] = []
    for component_runs in grouped.values():
        point_count = sum(x1 - x0 + 1 for _, x0, x1 in component_runs)
        points = np.empty((point_count, 2), dtype=np.int32)
        offset = 0
        for y, x0, x1 in component_runs:
            count = x1 - x0 + 1
            points[offset : offset + count, 0] = y
            points[offset : offset + count, 1] = np.arange(x0, x1 + 1, dtype=np.int32)
            offset += count
        components.append(points)
    return components


def bbox_from_points(points_yx: np.ndarray) -> list[int]:
    return [
        int(points_yx[:, 1].min()),
        int(points_yx[:, 0].min()),
        int(points_yx[:, 1].max()),
        int(points_yx[:, 0].max()),
    ]


def centroid_from_points(points_yx: np.ndarray) -> list[float]:
    return [float(points_yx[:, 1].mean()), float(points_yx[:, 0].mean())]
