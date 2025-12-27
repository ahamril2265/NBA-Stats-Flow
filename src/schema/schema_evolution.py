import yaml
from src.common.logger import get_logger

logger = get_logger("SCHEMA_EVOLUTION")


def load_schema(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def classify_schema_change(old: dict, new: dict):
    old_cols = {c["name"]: c for c in old["columns"]}
    new_cols = {c["name"]: c for c in new["columns"]}

    breaking_changes = []
    compatible_changes = []

    # Removed or changed columns
    for col_name, old_col in old_cols.items():
        if col_name not in new_cols:
            breaking_changes.append(f"Column removed: {col_name}")
        else:
            new_col = new_cols[col_name]
            if old_col["type"] != new_col["type"]:
                breaking_changes.append(
                    f"Type change: {col_name} ({old_col['type']} → {new_col['type']})"
                )
            if old_col.get("nullable", True) and not new_col.get("nullable", True):
                breaking_changes.append(
                    f"Nullable → non-nullable: {col_name}"
                )

    # New columns
    for col_name, new_col in new_cols.items():
        if col_name not in old_cols:
            if new_col.get("nullable", True):
                compatible_changes.append(f"New nullable column: {col_name}")
            else:
                breaking_changes.append(
                    f"New non-nullable column: {col_name}"
                )

    return breaking_changes, compatible_changes
