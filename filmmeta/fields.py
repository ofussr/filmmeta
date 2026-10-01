"""Film and equipment field definitions; no GUI dependencies."""

FIELDS = {
    "films": [
        ("manufacturer", "field.manufacturer"),
        ("name", "field.name"),
        ("iso", "field.iso"),
        ("process", "field.process"),
        ("alias", "field.alias"),
        ("grain", "field.grain"),
        ("type", "field.film_type"),
    ],
    "cameras": [("manufacturer", "field.manufacturer"), ("model", "field.model")],
    "lenses": [
        ("manufacturer", "field.manufacturer"),
        ("model", "field.model"),
        ("serial", "field.serial"),
    ],
    "scanners": [
        ("manufacturer", "field.manufacturer"),
        ("model", "field.model"),
        ("software", "field.software"),
    ],
}
FORM_FIELDS = {
    **FIELDS,
    "exposures": [
        ("number", "field.frame_number"),
        ("roll_id", "field.roll_id"),
        ("filter", "field.filter"),
    ],
    "developments": [
        ("manufacturer", "field.developer_maker"),
        ("name", "field.developer"),
        ("dilution", "field.dilution"),
        ("time", "field.develop_time"),
        ("lab", "field.lab"),
        ("lab_address", "field.lab_address"),
    ],
}
TITLES = {
    "films": "list.films",
    "cameras": "list.cameras",
    "lenses": "list.lenses",
    "scanners": "list.scanners",
}
ROLES = {
    "film": ("films", "role.film"),
    "camera": ("cameras", "role.camera"),
    "lens": ("lenses", "role.lens"),
    "scanner": ("scanners", "role.scanner"),
    "copy_camera": ("cameras", "role.copy_camera"),
    "copy_lens": ("lenses", "role.copy_lens"),
    "exposure": ("exposures", "role.exposure"),
    "development": ("developments", "role.development"),
}

FIELD_IDS = {
    f"{role}.{field}"
    for role, (kind, _) in ROLES.items()
    for field, _ in FORM_FIELDS[kind]
}
DEFAULT_VISIBLE = [
    f"{role}.{field}"
    for role, (kind, _) in ROLES.items()
    for field, _ in FORM_FIELDS[kind]
    if (role == "film" and field in {"manufacturer", "name", "iso", "process"})
    or (
        role in {"camera", "lens", "scanner", "copy_camera", "copy_lens"}
        and field in {"manufacturer", "model"}
    )
]
