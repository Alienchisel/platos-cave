#!/usr/bin/env python3
"""
mesh -> point cloud -> C header, for the T-QT Plato turntable.

Samples a mesh surface into an evenly-spaced point cloud, normalises it into a
signed-byte cube, and writes the C header the firmware compiles against.

    python sample_points.py ../mesh/plato.glb -n 3000 \
        -o ../firmware/plato_tqt/plato_points.h

Orientation flags exist because we cannot know which way the scan faces until
we look at it. Run preview.py after this to check, then come back and adjust.
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import trimesh

# The radius bisection deliberately probes values that under-fill, and trimesh
# warns on each one. Expected, and noisy.
trimesh.util.log.setLevel(logging.ERROR)

# The firmware stores each point as six signed bytes, so every coordinate and
# normal component has to land inside this range.
INT8_MAX = 127


def load_mesh(path: Path) -> trimesh.Trimesh:
    """Load any format trimesh handles, flattening scenes to a single mesh."""
    obj = trimesh.load(path, force="mesh")
    if not isinstance(obj, trimesh.Trimesh) or obj.faces.shape[0] == 0:
        sys.exit(f"error: {path} did not load as a mesh with faces")
    return obj


def orient(mesh: trimesh.Trimesh, yaw: float, pitch: float, roll: float,
           z_up: bool) -> None:
    """Rotate in place into the firmware's frame: +Y up, +Z toward the camera.

    Applied as roll, then pitch, then yaw, so yaw is the one you reach for when
    the head is upright but looking the wrong way.
    """
    if z_up:
        mesh.apply_transform(
            trimesh.transformations.rotation_matrix(np.radians(-90), [1, 0, 0]))
    for angle, axis in ((roll, [0, 0, 1]), (pitch, [1, 0, 0]), (yaw, [0, 1, 0])):
        if angle:
            mesh.apply_transform(
                trimesh.transformations.rotation_matrix(np.radians(angle), axis))


def crop_bottom(mesh: trimesh.Trimesh, fraction: float) -> trimesh.Trimesh:
    """Slice off the lowest `fraction` of the model's height.

    The Fitzwilliam scan ends in a ragged neck break. Spinning a torn edge looks
    like a glitch rather than an artefact, so we cut above it.

    Cuts at face granularity rather than slicing the plane exactly. The edge is
    jagged by one triangle, which is invisible once the surface becomes points,
    and it avoids trimesh's shapely dependency.
    """
    if fraction <= 0:
        return mesh
    lo, hi = mesh.bounds[0][1], mesh.bounds[1][1]
    plane_y = lo + (hi - lo) * fraction
    keep = mesh.triangles_center[:, 1] >= plane_y
    if not keep.any():
        sys.exit("error: --crop-bottom removed the whole mesh; use a smaller value")
    mesh.update_faces(keep)
    mesh.remove_unreferenced_vertices()
    print(f"  cropped bottom {fraction:.0%}: {len(mesh.faces)} faces remain")
    return mesh


def smooth(mesh: trimesh.Trimesh, iterations: int) -> trimesh.Trimesh:
    """Taubin-smooth before sampling, to tame photogrammetry normal noise.

    On a raw scan each face is a sliver of surface micro-detail, so its normal
    is near-random at the scale we care about. Sampling those directly turns the
    lambert term into salt-and-pepper. Taubin (unlike plain Laplacian) alternates
    shrink and inflate passes, so it kills the high frequencies without
    collapsing the form.
    """
    if iterations <= 0:
        return mesh
    trimesh.smoothing.filter_taubin(mesh, lamb=0.5, nu=0.53, iterations=iterations)
    print(f"  taubin-smoothed x{iterations}")
    return mesh


def sample(mesh: trimesh.Trimesh, count: int, seed: int):
    """Evenly-spaced surface samples plus the face normal at each one.

    Even spacing is the whole game. Poisson-disk sampling and then randomly
    discarding the surplus to hit an exact count re-introduces clumping: random
    removal from an evenly-spaced set leaves voids, and those voids read as
    black blotches hovering over the face.

    So instead we bisect on the disk radius until the sampler lands near the
    target, and keep every point it gives back. The exact count is unimportant --
    the generated header records whatever we end up with.
    """
    lo, hi = 0.0, 2.0 * float(np.sqrt(mesh.area / max(count, 1)))
    result = None
    for _ in range(14):
        r = (lo + hi) / 2
        pts, face_idx = trimesh.sample.sample_surface_even(
            mesh, count * 3, radius=r, seed=seed)
        result = (pts, face_idx)
        if len(pts) > count * 1.03:
            lo = r          # too dense: push the points further apart
        elif len(pts) < count * 0.97:
            hi = r
        else:
            break

    pts, face_idx = result
    print(f"  blue-noise sampled {len(pts)} points (target {count})")
    return pts, mesh.face_normals[face_idx]


def quantise(pts: np.ndarray, normals: np.ndarray):
    """Centre on the bounding box, scale to fill the byte range, pack to int8."""
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    pts = pts - (lo + hi) / 2.0
    half_extent = np.abs(pts).max()
    pts = pts / half_extent * INT8_MAX

    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    lengths[lengths == 0] = 1.0
    normals = normals / lengths * INT8_MAX

    pack = lambda a: np.clip(np.rint(a), -INT8_MAX, INT8_MAX).astype(np.int8)
    return pack(pts), pack(normals)


def write_header(path: Path, pts: np.ndarray, normals: np.ndarray,
                 source: str, argv: str) -> None:
    rows = []
    for (x, y, z), (nx, ny, nz) in zip(pts, normals):
        rows.append(f"  {{{x:4d},{y:4d},{z:4d},{nx:4d},{ny:4d},{nz:4d}}},")

    path.write_text(
        "// Generated by tools/sample_points.py -- do not edit by hand.\n"
        f"// source : {source}\n"
        f"// command: {argv}\n"
        "#pragma once\n"
        "#include <stdint.h>\n\n"
        f"#define PLATO_NUM_POINTS {len(pts)}\n\n"
        "// Six signed bytes per point: position xyz then normal xyz.\n"
        "// Positions fill [-127,127] on the longest axis; normals are unit * 127.\n"
        "// const at file scope lands in memory-mapped flash on the ESP32-S3,\n"
        "// so this costs no RAM and needs no PROGMEM accessors.\n"
        f"const int8_t plato_points[PLATO_NUM_POINTS][6] = {{\n"
        + "\n".join(rows) + "\n};\n",
        encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mesh", type=Path)
    ap.add_argument("-n", "--count", type=int, default=9000,
                    help="points to emit. 9000 with a 2px minimum dot gives ~73%% "
                         "coverage, which reads as Plato while keeping visible dot "
                         "texture. 6000 is dottier but speckly; 12000 goes solid")
    ap.add_argument("-o", "--out", type=Path,
                    default=Path(__file__).parent.parent /
                    "firmware" / "plato_tqt" / "plato_points.h")
    ap.add_argument("--npz", type=Path, help="also save raw floats for preview.py")
    ap.add_argument("--yaw", type=float, default=0.0)
    ap.add_argument("--pitch", type=float, default=0.0)
    ap.add_argument("--roll", type=float, default=0.0)
    ap.add_argument("--z-up", action="store_true",
                    help="source is Z-up (STL/PLY often are; GLB usually is not)")
    ap.add_argument("--crop-bottom", type=float, default=0.0,
                    help="cut this fraction off the base, e.g. 0.08 for a ragged neck")
    ap.add_argument("--smooth", type=int, default=12,
                    help="Taubin smoothing passes before sampling; raw scans need "
                         "this or the shading turns to noise (0 to disable)")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    mesh = load_mesh(args.mesh)
    print(f"loaded {args.mesh.name}: {len(mesh.faces)} faces, "
          f"extent {np.round(mesh.extents, 3)}")

    orient(mesh, args.yaw, args.pitch, args.roll, args.z_up)
    mesh = crop_bottom(mesh, args.crop_bottom)
    mesh = smooth(mesh, args.smooth)

    pts, normals = sample(mesh, args.count, args.seed)
    pts_q, normals_q = quantise(pts, normals)

    argv = "sample_points.py " + " ".join(sys.argv[1:])
    write_header(args.out, pts_q, normals_q, args.mesh.name, argv)
    print(f"wrote {len(pts_q)} points -> {args.out}  ({len(pts_q) * 6} bytes in flash)")

    if args.npz:
        np.savez(args.npz, pts=pts_q, normals=normals_q)
        print(f"wrote {args.npz}")


if __name__ == "__main__":
    main()
