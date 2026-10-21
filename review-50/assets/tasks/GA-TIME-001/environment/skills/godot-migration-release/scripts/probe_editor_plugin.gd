@tool
extends EditorPlugin

func _enter_tree() -> void:
    call_deferred("capture_parser")

func capture_parser() -> void:
    await get_tree().create_timer(0.5).timeout
    var parser = load("res://addons/quest_text_parser.gd").new()
    var extracted: Array = parser._parse_file("res://data/dialogue.quest")
    var rows: Array = []
    for entry in extracted:
        rows.append(Array(entry))
    var extensions := Array(parser._get_recognized_extensions())
    parser = null
    print("QUESTBOARD_OBSERVATION=" + JSON.stringify({"entries":rows,"extensions":extensions}))
    get_tree().quit(0)
