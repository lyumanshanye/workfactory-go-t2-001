@tool
extends EditorTranslationParserPlugin

func _get_recognized_extensions() -> PackedStringArray:
    return PackedStringArray(["quest"])

func _parse_file(path: String) -> Array[PackedStringArray]:
    var result: Array[PackedStringArray] = []
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return result
    for line in file.get_as_text().split("\n"):
        var clean: String = line.strip_edges()
        if clean.is_empty() or clean.begins_with("#"):
            continue
        var columns := clean.split("|", true)
        if columns[0].strip_edges().is_empty():
            continue
        var entry := PackedStringArray()
        for column in columns:
            entry.append(column.strip_edges())
        result.append(entry)
    return result
