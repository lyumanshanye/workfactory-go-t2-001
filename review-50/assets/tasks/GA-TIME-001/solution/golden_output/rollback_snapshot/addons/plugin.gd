@tool
extends EditorPlugin
var quest_parser: EditorTranslationParserPlugin

func _enter_tree() -> void:
    quest_parser = preload("res://addons/quest_text_parser.gd").new()
    add_translation_parser_plugin(quest_parser)

func _exit_tree() -> void:
    if quest_parser != null:
        remove_translation_parser_plugin(quest_parser)
        quest_parser = null
