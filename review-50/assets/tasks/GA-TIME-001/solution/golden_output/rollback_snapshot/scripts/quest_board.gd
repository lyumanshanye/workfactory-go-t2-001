extends Control
var board: GraphEdit
var last_rects: Dictionary = {}
var status_label: Label

func _ready() -> void:
    var title := Label.new()
    title.text = "Quest Board · historical interface baseline (not release approval)"
    title.position = Vector2(20, 12)
    add_child(title)
    board = GraphEdit.new()
    board.name = "Board"
    board.position = Vector2(20, 60)
    board.size = Vector2(900, 450)
    board.frame_rect_changed.connect(_on_frame_rect_changed)
    add_child(board)
    var frame := GraphFrame.new()
    frame.name = "ChapterOne"
    frame.title = "Chapter 1"
    frame.position_offset = Vector2(50, 50)
    frame.size = Vector2(380, 240)
    frame.resizable = true
    board.add_child(frame)
    for i in range(2):
        var quest := GraphNode.new()
        quest.name = "Quest" + str(i)
        quest.title = ["Visit the market", "Return to the gate"][i]
        quest.position_offset = Vector2(90 + i * 220, 100)
        var text := Label.new()
        text.text = "Original synthetic quest fixture"
        quest.add_child(text)
        board.add_child(quest)
    status_label = Label.new()
    status_label.position = Vector2(20, 540)
    status_label.text = "Resize the Chapter 1 frame to record its full Rect2."
    add_child(status_label)

func _on_frame_rect_changed(frame: GraphFrame, new_rect: Vector2) -> void:
    last_rects[String(frame.name)] = {"size": [new_rect.x, new_rect.y]}
    if is_instance_valid(status_label):
        status_label.text = String(frame.name) + ": " + str(new_rect)
