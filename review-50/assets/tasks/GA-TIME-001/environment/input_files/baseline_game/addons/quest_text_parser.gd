@tool
extends EditorTranslationParserPlugin
func _get_recognized_extensions() -> PackedStringArray:
    return PackedStringArray(["quest"])
func _parse_file(path: String, msgids: Array[String], msgids_context_plural: Array[Array]) -> void:
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        return
    for line in file.get_as_text().split("\n"):
        var clean: String = line.strip_edges()
        if clean.is_empty() or clean.begins_with("#"):
            continue
        var columns := clean.split("|", true)
        if columns[0].strip_edges().is_empty():
            continue
        var context: String = columns[1].strip_edges() if columns.size() > 1 else ""
        var plural: String = columns[2].strip_edges() if columns.size() > 2 else ""
        msgids_context_plural.append([columns[0].strip_edges(), context, plural])
