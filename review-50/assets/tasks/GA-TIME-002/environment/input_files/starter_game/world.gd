extends Node2D

var shots := 0
var steps := 0
var ticks := 0
var player := Vector2(350, 320)
var target := Vector2(-100, -100)

func _ready() -> void:
    process_mode = Node.PROCESS_MODE_PAUSABLE

func _physics_process(_delta: float) -> void:
    ticks += 1

func _input(event: InputEvent) -> void:
    if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
        shots += 1
        target = event.position
        get_viewport().set_input_as_handled()
        queue_redraw()
    elif event is InputEventKey and event.pressed and not event.echo:
        if event.keycode == KEY_RIGHT:
            steps += 1
            player.x += 20
            get_viewport().set_input_as_handled()
            queue_redraw()
        elif event.keycode == KEY_SPACE:
            shots += 1
            target = player + Vector2(90, 0)
            get_viewport().set_input_as_handled()
            queue_redraw()

func _draw() -> void:
    var extent := get_viewport_rect().size
    draw_rect(Rect2(Vector2.ZERO, extent), Color("0b1727"))
    for x in range(0, int(extent.x), 40):
        draw_line(Vector2(x,0), Vector2(x,extent.y), Color("16283b"))
    for y in range(0, int(extent.y), 40):
        draw_line(Vector2(0,y), Vector2(extent.x,y), Color("16283b"))
    draw_circle(player, 22, Color("56d6be"))
    draw_circle(player, 10, Color("163a47"))
    if target.x >= 0:
        draw_line(player, target, Color("ffce79"), 3)
        draw_arc(target, 12, 0, TAU, 24, Color("ffce79"), 2)
