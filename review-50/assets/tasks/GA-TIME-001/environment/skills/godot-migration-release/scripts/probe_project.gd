extends SceneTree

func _initialize() -> void:
    call_deferred("run_probe")

func emit_result(result: Dictionary) -> void:
    print("QUESTBOARD_OBSERVATION=" + JSON.stringify(result))
    call_deferred("quit", 0)

func run_probe() -> void:
    var mode := OS.get_cmdline_user_args()[0]
    if mode == "ui":
        var scene = load("res://main.tscn").instantiate()
        root.add_child(scene)
        await process_frame
        var frame: GraphFrame = scene.board.get_node("ChapterOne")
        scene.board.frame_rect_changed.emit(frame, Rect2(13, 27, 321, 189))
        emit_result({"frame_name":String(frame.name),"observed":scene.last_rects.get("ChapterOne"),"node_count":scene.board.get_child_count()})
    elif mode == "stdin":
        var reader = load("res://scripts/stdin_importer.gd").new()
        emit_result({"checkpoint":reader.read_checkpoint()})
    else:
        emit_result({"error":"unknown runtime probe"})
