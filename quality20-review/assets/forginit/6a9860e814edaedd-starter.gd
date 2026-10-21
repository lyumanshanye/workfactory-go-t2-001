extends SceneTree

const SOURCE_V2_AT := "2026-10-20T00:00:00Z"
const MAX_DURATION := 86400000


func fail(message: String) -> void:
    push_error(message)
    quit(2)


func valid_time(value: Variant) -> bool:
    if typeof(value) != TYPE_STRING:
        return false
    var pattern := RegEx.new()
    pattern.compile("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
    if pattern.search(value) == null:
        return false
    var normalized := Time.get_datetime_string_from_unix_time(Time.get_unix_time_from_datetime_string(value)) + "Z"
    return normalized == value


func number(value: Variant) -> bool:
    return (typeof(value) == TYPE_FLOAT or typeof(value) == TYPE_INT) and is_finite(float(value))


func same_payload(left: Dictionary, right: Dictionary) -> bool:
    return (left.size() == 3 and right.size() == 3
            and left.get("event_name") == right.get("event_name")
            and left.get("session_id") == right.get("session_id")
            and number(left.get("duration_ms")) and number(right.get("duration_ms"))
            and float(left["duration_ms"]) == float(right["duration_ms"]))


func select_policy(config: Dictionary, approvals: Array) -> Dictionary:
    var cutoff: String = config["as_of"]
    var eligible: Array = []
    for policy in config["policies"]:
        if not valid_time(policy["effective_at"]) or policy["effective_at"] > cutoff:
            continue
        var authorized := false
        for approval in approvals:
            if (approval.get("policy") == policy["id"] and approval.get("action") == "approve"
                    and true
                    and valid_time(approval.get("at")) and valid_time(approval.get("received_at"))
                    and approval["at"] <= cutoff and approval["received_at"] <= cutoff):
                authorized = true
        if authorized:
            eligible.append(policy)
    eligible.sort_custom(func(a, b): return a["effective_at"] > b["effective_at"])
    if eligible.is_empty():
        return {}
    if eligible.size() > 1 and eligible[0]["effective_at"] == eligible[1]["effective_at"]:
        return {}
    return eligible[0]


func normalize(event: Dictionary) -> Dictionary:
    for field in ["event_id", "session_id"]:
        if typeof(event.get(field)) != TYPE_STRING or event[field].is_empty():
            return {"error": "invalid_" + field}
    for field in ["occurred_at", "received_at"]:
        if not valid_time(event.get(field)):
            return {"error": "invalid_" + field}
    if event["received_at"] < event["occurred_at"]:
        return {"error": "received_before_occurrence"}
    var source_v2: bool = event["received_at"] >= SOURCE_V2_AT
    if not number(event.get("schema")) or event["schema"] != (2 if source_v2 else 1):
        return {"error": "schema_time_mismatch"}
    var amount: Variant = event.get("duration_ms" if source_v2 else "duration_seconds")
    if not number(amount):
        return {"error": "invalid_duration"}
    var milliseconds: float = float(amount) if source_v2 else float(amount) * 1000.0
    if milliseconds < 0 or milliseconds > MAX_DURATION or milliseconds != floor(milliseconds):
        return {"error": "invalid_duration"}
    if event.get("event_name" if source_v2 else "kind") != ("level_complete" if source_v2 else "win"):
        return {"error": "invalid_event_name"}
    return {"payload": {"event_name": "level_complete", "session_id": event["session_id"],
                         "duration_ms": int(milliseconds)}}


func migrate(lines: Array, checkpoint: Dictionary, config: Dictionary, policy: Dictionary) -> Dictionary:
    var decisions: Array = []
    var groups: Dictionary = {}
    var additions: Dictionary = {}
    var blocked := false
    for index in range(lines.size()):
        var decision := {"line": index + 1, "event_id": "", "status": "", "detail": ""}
        decisions.append(decision)
        var parser := JSON.new()
        if parser.parse(lines[index]) != OK:
            decision["status"] = "invalid_json"
            decision["detail"] = "parser_line=%d: %s" % [parser.get_error_line(), parser.get_error_message()]
            continue
        var event: Variant = parser.data
        if typeof(event) != TYPE_DICTIONARY:
            decision["status"] = "invalid_root"
            continue
        if typeof(event.get("event_id")) == TYPE_STRING:
            decision["event_id"] = event["event_id"]
        if not valid_time(event.get("received_at")):
            decision["status"] = "invalid_received_at"
            continue
        if event["received_at"] > config["as_of"]:
            decision["status"] = "next_batch"
            continue
        var normalized := normalize(event)
        if normalized.has("error"):
            decision["status"] = normalized["error"]
            continue
        var key: String = event["event_id"]
        if not groups.has(key):
            groups[key] = []
        groups[key].append({"index": index, "payload": normalized["payload"]})
    for key in groups:
        var group: Array = groups[key]
        var first: Dictionary = group[0]["payload"]
        var conflict := false
        for item in group:
            conflict = conflict or not same_payload(item["payload"], first)
        var historical_conflict: bool = checkpoint.has(key) and (checkpoint[key] != first or conflict)
        blocked = blocked or historical_conflict
        for position in range(group.size()):
            var item: Dictionary = group[position]
            var status: String
            if historical_conflict:
                status = "checkpoint_conflict"
            elif conflict and policy["conflict_mode"] == "quarantine_group":
                status = "batch_conflict"
            elif conflict and policy["conflict_mode"] == "keep_last":
                status = "accepted" if position == group.size() - 1 else "superseded"
            elif checkpoint.has(key):
                status = "already_committed"
            else:
                status = "accepted" if position == 0 else "duplicate"
            if status == "accepted":
                additions[key] = item["payload"].duplicate(true)
            decisions[item["index"]]["status"] = status
    var counts: Dictionary = {}
    for row in decisions:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return {"policy": policy["id"], "as_of": config["as_of"], "decisions": decisions,
            "counts": counts, "additions": additions, "new_unique_events": additions.size(),
            "publication_blocked": blocked, "checkpoint_unchanged": true,
            "scope": "Original simulated telemetry acceptance exercise, not real player data."}


func read_json(path: String) -> Variant:
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return null
    var parser := JSON.new()
    if parser.parse(file.get_as_text()) != OK:
        return null
    return parser.data


func _initialize() -> void:
    var arguments := OS.get_cmdline_user_args()
    if arguments.size() != 4 or arguments[0] != "--inputs" or arguments[2] != "--output":
        fail("Expected -- --inputs INPUT_DIRECTORY --output OUTPUT_DIRECTORY")
        return
    var inputs: String = arguments[1]
    var output: String = arguments[3]
    var config: Variant = read_json(inputs.path_join("policies.json"))
    var approvals: Variant = read_json(inputs.path_join("approvals.json"))
    var checkpoint: Variant = read_json(inputs.path_join("checkpoint.json"))
    if typeof(config) != TYPE_DICTIONARY or typeof(approvals) != TYPE_ARRAY or typeof(checkpoint) != TYPE_DICTIONARY:
        fail("Invalid configuration, approval or checkpoint file")
        return
    if not valid_time(config.get("as_of")):
        fail("Invalid freeze timestamp")
        return
    var policy := select_policy(config, approvals)
    if policy.is_empty() or policy.get("conflict_mode") not in ["quarantine_group", "keep_last"]:
        fail("Cannot select a unique authorized policy")
        return
    var file := FileAccess.open(inputs.path_join("events.jsonl"), FileAccess.READ)
    if file == null:
        fail("Cannot open original events")
        return
    var lines: Array = []
    while file.get_position() < file.get_length():
        lines.append(file.get_line())
    file.close()
    var result := migrate(lines, checkpoint, config, policy)
    var hashes: Dictionary = {}
    for name in ["policies.json", "approvals.json", "checkpoint.json", "events.jsonl"]:
        hashes[name] = FileAccess.get_sha256(inputs.path_join(name))
    result["input_sha256"] = hashes
    if DirAccess.make_dir_recursive_absolute(output) != OK:
        fail("Cannot create output directory")
        return
    var report := FileAccess.open(output.path_join("run_report.json"), FileAccess.WRITE)
    var csv := FileAccess.open(output.path_join("decisions.csv"), FileAccess.WRITE)
    if report == null or csv == null:
        fail("Cannot open output files")
        return
    report.store_string(JSON.stringify(result, "  ") + "\n")
    csv.store_csv_line(PackedStringArray(["line", "event_id", "status", "detail"]))
    for row in result["decisions"]:
        csv.store_csv_line(PackedStringArray([str(row["line"]), row["event_id"], row["status"], row["detail"]]))
    report.close()
    csv.close()
    print(JSON.stringify({"policy": result["policy"], "new_unique_events": result["new_unique_events"], "publication_blocked": result["publication_blocked"]}))
    quit(0)
