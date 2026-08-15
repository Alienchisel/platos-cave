#!/usr/bin/env python3
"""
Build a crude stand-in head so the pipeline can be exercised without the scan.

Deliberately asymmetric -- skull, nose, brow, beard -- because a symmetric blob
would hide orientation and backface-culling mistakes. Replace with the real
Fitzwilliam mesh as soon as you have it.
"""

from pathlib import Path

import numpy as np
import trimesh


def blob(radius, scale, translate):
    m = trimesh.creation.icosphere(subdivisions=4, radius=radius)
    m.apply_scale(scale)
    m.apply_translation(translate)
    return m


parts = [
    blob(1.0, (0.86, 1.10, 1.00), (0.0, 0.10, 0.0)),      # cranium
    blob(0.42, (0.70, 0.55, 1.30), (0.0, -0.10, 0.55)),   # face mass, forward
    blob(0.16, (0.55, 0.90, 1.60), (0.0, -0.10, 0.92)),   # nose
    blob(0.30, (1.05, 0.30, 0.55), (0.0, 0.52, 0.72)),    # brow ridge
    blob(0.62, (0.82, 0.95, 0.85), (0.0, -0.85, 0.32)),   # beard
    blob(0.22, (0.35, 0.75, 0.40), (0.78, 0.05, 0.05)),   # ears
    blob(0.22, (0.35, 0.75, 0.40), (-0.78, 0.05, 0.05)),
]

mesh = trimesh.util.concatenate(parts)
out = Path(__file__).parent.parent / "mesh" / "test_head.stl"
mesh.export(out)
print(f"wrote {out}: {len(mesh.faces)} faces, extents {np.round(mesh.extents, 3)}")
