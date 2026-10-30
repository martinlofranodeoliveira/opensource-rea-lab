_PAYLOAD_ERROR = "Invalid entry presence payload or budget"
_CLAIM_ERROR = "Invalid entrypoint claim declaration"
_EVIDENCE_ERROR = "Invalid inventory evidence declaration"
_DEFAULT_MAX_TARGETS = 32
_DEFAULT_MAX_FILES = 1000
_MAX_TARGETS_LIMIT = 64
_MAX_FILES_LIMIT = 2000
_MIN_BUDGET = 1
_MIN_ENTRY_LENGTH = 1
_MAX_ENTRY_LENGTH = 256
def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_PAYLOAD_ERROR)
    found_targets = False
    found_inventory = False
    for key in payload:
        if key == "targets":
            found_targets = True
        elif key == "inventory":
            found_inventory = True
        elif key == "max_targets":
            pass
        elif key == "max_files":
            pass
        else:
            raise ValueError(_PAYLOAD_ERROR)
    if not found_targets:
        raise ValueError(_PAYLOAD_ERROR)
    if not found_inventory:
        raise ValueError(_PAYLOAD_ERROR)
    if "max_targets" in payload:
        max_targets_value = payload["max_targets"]
        if type(max_targets_value) is not int:
            raise ValueError(_PAYLOAD_ERROR)
        if max_targets_value < _MIN_BUDGET:
            raise ValueError(_PAYLOAD_ERROR)
        if max_targets_value > _MAX_TARGETS_LIMIT:
            raise ValueError(_PAYLOAD_ERROR)
    else:
        max_targets_value = _DEFAULT_MAX_TARGETS
    if "max_files" in payload:
        max_files_value = payload["max_files"]
        if type(max_files_value) is not int:
            raise ValueError(_PAYLOAD_ERROR)
        if max_files_value < _MIN_BUDGET:
            raise ValueError(_PAYLOAD_ERROR)
        if max_files_value > _MAX_FILES_LIMIT:
            raise ValueError(_PAYLOAD_ERROR)
    else:
        max_files_value = _DEFAULT_MAX_FILES
    targets_value = payload["targets"]
    inventory_value = payload["inventory"]
    if not isinstance(targets_value, list):
        raise ValueError(_CLAIM_ERROR)
    if len(targets_value) > max_targets_value:
        raise ValueError(_CLAIM_ERROR)
    if not isinstance(inventory_value, list):
        raise ValueError(_EVIDENCE_ERROR)
    if len(inventory_value) > max_files_value:
        raise ValueError(_EVIDENCE_ERROR)
    target_copies = []
    seen_targets = set()
    for entry in targets_value:
        if not isinstance(entry, str):
            raise ValueError(_CLAIM_ERROR)
        plain = str(entry)
        if len(plain) < _MIN_ENTRY_LENGTH:
            raise ValueError(_CLAIM_ERROR)
        if len(plain) > _MAX_ENTRY_LENGTH:
            raise ValueError(_CLAIM_ERROR)
        if plain in seen_targets:
            raise ValueError(_CLAIM_ERROR)
        seen_targets.add(plain)
        target_copies.append(plain)
    inventory_copies = []
    seen_inventory = set()
    for entry in inventory_value:
        if not isinstance(entry, str):
            raise ValueError(_EVIDENCE_ERROR)
        plain = str(entry)
        if len(plain) < _MIN_ENTRY_LENGTH:
            raise ValueError(_EVIDENCE_ERROR)
        if len(plain) > _MAX_ENTRY_LENGTH:
            raise ValueError(_EVIDENCE_ERROR)
        if plain in seen_inventory:
            raise ValueError(_EVIDENCE_ERROR)
        seen_inventory.add(plain)
        inventory_copies.append(plain)
    present_items = []
    missing_items = []
    for item in target_copies:
        if item in seen_inventory:
            present_items.append(str(item))
        else:
            missing_items.append(str(item))
    sorted_present = sorted(present_items)
    sorted_missing = sorted(missing_items)
    final_present = []
    for value in sorted_present:
        final_present.append(str(value))
    final_missing = []
    for value in sorted_missing:
        final_missing.append(str(value))
    total_value = len(target_copies)
    present_count_value = len(final_present)
    missing_count_value = len(final_missing)
    if len(final_missing) == 0:
        complete_flag = True
    else:
        complete_flag = False
    result = {}
    result["total"] = total_value
    result["present_count"] = present_count_value
    result["missing_count"] = missing_count_value
    result["present"] = final_present
    result["missing"] = final_missing
    result["is_complete"] = complete_flag
    return result
