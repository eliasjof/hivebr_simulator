"""Small, dependency-free URDF reader and forward-kinematics helper.

The browser simulator only needs the subset of URDF used by the didactic
SCARA cell: links with primitive visuals, revolute/prismatic/fixed joints,
joint origins, axes and limits.  Keeping the parser here means the student
can edit the URDF file as a normal editor tab and the Python simulator and
the canvas renderer see exactly the same model.

The public helpers are deliberately simple:

    model = load_model("scara_cell.urdf")
    transforms = chain_transforms(model, {"joint_1": 0.2, ...})
    x, y, z = tip(model, {"q1": 0.2, "q2": -0.4, "d3": -0.1})

No ROS installation is required.
"""
from __future__ import annotations

import math
import os
import xml.etree.ElementTree as ET

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
DEFAULT_URDF = os.path.join(MODEL_DIR, "scara_cell.urdf")


# ------------------------------------------------------------------ maths ----
def identity():
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def multiply(a, b):
    return [
        [sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)]
        for i in range(4)
    ]


def translation(x, y, z):
    m = identity()
    m[0][3], m[1][3], m[2][3] = float(x), float(y), float(z)
    return m


def rotation_x(angle):
    c, s = math.cos(angle), math.sin(angle)
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, c, -s, 0.0],
        [0.0, s, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def rotation_y(angle):
    c, s = math.cos(angle), math.sin(angle)
    return [
        [c, 0.0, s, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [-s, 0.0, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def rotation_z(angle):
    c, s = math.cos(angle), math.sin(angle)
    return [
        [c, -s, 0.0, 0.0],
        [s, c, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def rpy_matrix(roll, pitch, yaw):
    """URDF fixed-axis roll/pitch/yaw: R = Rz(yaw) Ry(pitch) Rx(roll)."""
    return multiply(multiply(rotation_z(yaw), rotation_y(pitch)), rotation_x(roll))


def axis_angle(axis, angle):
    ax, ay, az = (float(v) for v in axis)
    norm = math.sqrt(ax * ax + ay * ay + az * az)
    if norm <= 1e-12:
        return identity()
    ax, ay, az = ax / norm, ay / norm, az / norm
    c, s = math.cos(angle), math.sin(angle)
    k = 1.0 - c
    return [
        [c + ax * ax * k, ax * ay * k - az * s, ax * az * k + ay * s, 0.0],
        [ay * ax * k + az * s, c + ay * ay * k, ay * az * k - ax * s, 0.0],
        [az * ax * k - ay * s, az * ay * k + ax * s, c + az * az * k, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def transform_point(matrix, point):
    x, y, z = (float(v) for v in point)
    return [
        matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * z + matrix[0][3],
        matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * z + matrix[1][3],
        matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * z + matrix[2][3],
    ]


def translation_of(matrix):
    return [matrix[0][3], matrix[1][3], matrix[2][3]]


# ------------------------------------------------------------------ parse ----
def _numbers(text, default):
    try:
        values = [float(part) for part in str(text).replace(",", " ").split()]
    except (TypeError, ValueError):
        return list(default)
    return values


def _triple(text, default):
    values = _numbers(text, default)
    values = (values + list(default))[:3]
    return [float(v) for v in values]


def _origin(node):
    origin = node.find("origin") if node is not None else None
    if origin is None:
        return {"xyz": [0.0, 0.0, 0.0], "rpy": [0.0, 0.0, 0.0]}
    return {
        "xyz": _triple(origin.get("xyz", "0 0 0"), [0.0, 0.0, 0.0]),
        "rpy": _triple(origin.get("rpy", "0 0 0"), [0.0, 0.0, 0.0]),
    }


def _geometry(node):
    if node is None:
        return None
    geometry = node.find("geometry")
    if geometry is None:
        return None
    box = geometry.find("box")
    if box is not None:
        return {"type": "box", "size": _triple(box.get("size", "1 1 1"), [1.0, 1.0, 1.0])}
    cylinder = geometry.find("cylinder")
    if cylinder is not None:
        return {
            "type": "cylinder",
            "radius": float(cylinder.get("radius", 0.1)),
            "length": float(cylinder.get("length", 0.1)),
        }
    sphere = geometry.find("sphere")
    if sphere is not None:
        return {"type": "sphere", "radius": float(sphere.get("radius", 0.1))}
    mesh = geometry.find("mesh")
    if mesh is not None:
        return {
            "type": "mesh",
            "filename": mesh.get("filename", ""),
            "scale": _triple(mesh.get("scale", "1 1 1"), [1.0, 1.0, 1.0]),
        }
    return None


def _material(visual, materials):
    material = visual.find("material") if visual is not None else None
    if material is None:
        return None
    color_node = material.find("color")
    color = None
    if color_node is not None:
        rgba = _numbers(color_node.get("rgba", "0.7 0.7 0.7 1"), [0.7, 0.7, 0.7, 1.0])
        rgba = (rgba + [0.7, 0.7, 0.7, 1.0])[:4]
        color = [float(v) for v in rgba]
    name = material.get("name", "")
    if color is None and name in materials:
        color = materials[name]
    if color is None:
        return None
    return {"name": name, "color": color}


def _visual(visual, materials):
    geometry = _geometry(visual)
    if geometry is None:
        return None
    return {
        "origin": _origin(visual),
        "geometry": geometry,
        "material": _material(visual, materials),
    }


def _longest_chain(children, link, visited):
    best = []
    for joint in children.get(link, []):
        child = joint["child"]
        if child in visited:
            continue
        path = [joint] + _longest_chain(children, child, visited | {child})
        if len(path) > len(best):
            best = path
    return best


def parse_urdf(text):
    """Parses URDF text into a JSON-friendly model dictionary."""
    root = ET.fromstring(text)
    if root.tag != "robot":
        raise ValueError("URDF root element must be <robot>")

    materials = {}
    for material in root.findall("material"):
        name = material.get("name")
        color_node = material.find("color")
        if name and color_node is not None:
            rgba = _numbers(color_node.get("rgba", "0.7 0.7 0.7 1"), [0.7, 0.7, 0.7, 1.0])
            materials[name] = [float(v) for v in (rgba + [0.7, 0.7, 0.7, 1.0])[:4]]

    links = {}
    for link in root.findall("link"):
        name = link.get("name")
        if not name:
            continue
        visuals = [v for v in (_visual(node, materials) for node in link.findall("visual")) if v]
        collisions = [v for v in (_visual(node, materials) for node in link.findall("collision")) if v]
        links[name] = {"name": name, "visuals": visuals, "collisions": collisions}

    joints = []
    for joint in root.findall("joint"):
        name = joint.get("name")
        parent = joint.find("parent")
        child = joint.find("child")
        if not name or parent is None or child is None:
            continue
        axis_node = joint.find("axis")
        axis = _triple(axis_node.get("xyz", "1 0 0"), [1.0, 0.0, 0.0]) if axis_node is not None else [1.0, 0.0, 0.0]
        limit_node = joint.find("limit")
        limit = {}
        if limit_node is not None:
            for key in ("lower", "upper", "effort", "velocity"):
                if limit_node.get(key) is not None:
                    limit[key] = float(limit_node.get(key))
        joints.append({
            "name": name,
            "type": joint.get("type", "fixed"),
            "parent": parent.get("link"),
            "child": child.get("link"),
            "origin": _origin(joint),
            "axis": axis,
            "limit": limit,
        })

    child_links = {joint["child"] for joint in joints}
    roots = [name for name in links if name not in child_links]
    base = roots[0] if roots else (next(iter(links), "base_link"))
    children = {}
    for joint in joints:
        children.setdefault(joint["parent"], []).append(joint)
    chain = _longest_chain(children, base, {base})

    # Friendly motion names used by the student API. The number is the joint
    # position in the main chain, so the didactic SCARA is q1, q2 and d3:
    # joint_3 is the third joint and it is prismatic.
    for index, joint in enumerate(chain):
        if joint["type"] in ("revolute", "continuous"):
            joint["motion"] = f"q{index + 1}"
        elif joint["type"] == "prismatic":
            joint["motion"] = f"d{index + 1}"
        else:
            joint["motion"] = ""

    def _axis_length(joint):
        xyz = joint["origin"]["xyz"]
        return math.hypot(xyz[0], xyz[1])

    base_z = chain[0]["origin"]["xyz"][2] if chain else 0.0
    l1 = _axis_length(chain[1]) if len(chain) > 1 else 0.0
    l2 = _axis_length(chain[2]) if len(chain) > 2 else 0.0
    tool = chain[-1]["child"] if chain else base

    return {
        "name": root.get("name", "robot"),
        "base": base,
        "tool": tool,
        "links": links,
        "joints": joints,
        "chain": chain,
        "materials": materials,
        "lengths": {
            "l1": l1,
            "l2": l2,
            "base_z": base_z,
            "reach": l1 + l2,
        },
    }


# ------------------------------------------------------------------ files ----
def _candidates(model_path):
    if model_path:
        path = os.path.expanduser(str(model_path))
        if os.path.isabs(path):
            return [path]
        return [
            os.path.join(os.getcwd(), path),
            os.path.join(os.getcwd(), "user_scripts", path),
            os.path.join(MODEL_DIR, os.path.basename(path)),
        ]
    env_path = os.environ.get("HIVEBR_SCARA_URDF")
    if env_path:
        return [os.path.expanduser(env_path), DEFAULT_URDF]
    return [
        os.path.join(os.getcwd(), "user_scripts", "scara_cell.urdf"),
        os.path.join(os.getcwd(), "scara_cell.urdf"),
        DEFAULT_URDF,
    ]


def resolve_model_path(model_path=None):
    for candidate in _candidates(model_path):
        if os.path.isfile(candidate):
            return candidate
    return DEFAULT_URDF


def load_model(model_path=None):
    path = resolve_model_path(model_path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        raise ValueError(f"could not read URDF {path!r}: {exc}") from exc
    try:
        model = parse_urdf(text)
    except ET.ParseError as exc:
        raise ValueError(f"invalid URDF {os.path.basename(path)}: {exc}") from exc
    model["source"] = path
    return model


# ---------------------------------------------------------- kinematics ----
def _value_for(joint, values):
    motion = joint.get("motion")
    if motion and isinstance(values, dict) and motion in values:
        return float(values[motion])
    if isinstance(values, dict):
        return float(values.get(joint["name"], 0.0))
    try:
        index = joint.get("_index", 0)
        return float(values[index])
    except (TypeError, IndexError):
        return 0.0


def motion_matrix(joint, value):
    kind = joint["type"]
    if kind in ("revolute", "continuous"):
        return axis_angle(joint["axis"], value)
    if kind == "prismatic":
        axis = joint["axis"]
        norm = math.sqrt(sum(float(v) * float(v) for v in axis)) or 1.0
        return translation(*(float(v) / norm * value for v in axis))
    return identity()


def origin_matrix(joint):
    origin = joint["origin"]
    return multiply(
        translation(*origin["xyz"]),
        rpy_matrix(*origin["rpy"]),
    )


def joint_transform(joint, value):
    return multiply(origin_matrix(joint), motion_matrix(joint, value))


def chain_transforms(model, values):
    """World transform of every link in the main chain.

    ``values`` may be a dict keyed by motion name (q1, q2, d3) or joint name.
    """
    transforms = {model["base"]: identity()}
    current = identity()
    for index, joint in enumerate(model["chain"]):
        joint["_index"] = index
        current = multiply(current, joint_transform(joint, _value_for(joint, values)))
        transforms[joint["child"]] = current
    return transforms


def joint_positions(model, values):
    transforms = chain_transforms(model, values)
    return {
        joint["name"]: translation_of(transforms.get(joint["child"], identity()))
        for joint in model["chain"]
    }


def tip(model, values):
    transforms = chain_transforms(model, values)
    return translation_of(transforms.get(model["tool"], identity()))


def model_summary(model):
    """Compact description used by the URDF activity and tests."""
    return {
        "name": model.get("name"),
        "links": len(model.get("links", {})),
        "joints": len(model.get("chain", [])),
        "l1": round(float(model["lengths"]["l1"]), 4),
        "l2": round(float(model["lengths"]["l2"]), 4),
        "base_z": round(float(model["lengths"]["base_z"]), 4),
        "types": [joint["type"] for joint in model.get("chain", [])],
        "source": os.path.basename(model.get("source", "")),
    }
