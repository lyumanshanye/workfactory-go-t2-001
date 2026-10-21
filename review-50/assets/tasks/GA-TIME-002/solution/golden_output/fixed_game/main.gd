extends Node2D

var world: Node2D
var menu_button: Button
var overlay: ColorRect
var panel: Panel
var resume_button: Button
var volume: HSlider
var alias_field: LineEdit
var hud: Label
var menu_open := false

func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    world = load("res://world.gd").new()
    world.name = "World"
    add_child(world)
    var layer := CanvasLayer.new()
    add_child(layer)
    var ui := Control.new()
    layer.add_child(ui)
    ui.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    ui.mouse_filter = Control.MOUSE_FILTER_IGNORE
    menu_button = Button.new()
    menu_button.name = "MenuButton"
    menu_button.text = "      PAUSE / ESC"
    menu_button.position = Vector2(24,24)
    menu_button.size = Vector2(160,44)
    ui.add_child(menu_button)
    menu_button.pressed.connect(func(): set_menu(true))
    var icon := ColorRect.new()
    icon.name = "DecorativeIcon"
    icon.color = Color("56d6be")
    icon.position = Vector2(12,14)
    icon.size = Vector2(14,16)
    icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
    menu_button.add_child(icon)
    hud = Label.new()
    hud.position = Vector2(24,84)
    hud.mouse_filter = Control.MOUSE_FILTER_IGNORE
    ui.add_child(hud)
    overlay = ColorRect.new()
    overlay.name = "ModalBackdrop"
    overlay.color = Color(0.01,0.025,0.05,0.88)
    overlay.mouse_filter = Control.MOUSE_FILTER_STOP
    ui.add_child(overlay)
    overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    overlay.gui_input.connect(func(event):
        if event is InputEventMouse: overlay.accept_event())
    panel = Panel.new()
    panel.name = "SettingsPanel"
    overlay.add_child(panel)
    panel.size = Vector2(360,300)
    var title := Label.new()
    title.text = "PAUSED  /  INPUT HARBOUR"
    title.position = Vector2(24,22)
    title.add_theme_font_size_override("font_size",19)
    title.mouse_filter = Control.MOUSE_FILTER_IGNORE
    panel.add_child(title)
    var description := Label.new()
    description.text = "UI stays live. World waits.\nBackdrop clicks are absorbed."
    description.position = Vector2(24,57)
    description.mouse_filter = Control.MOUSE_FILTER_IGNORE
    panel.add_child(description)
    volume = HSlider.new()
    volume.name = "Volume"
    volume.position = Vector2(24,112)
    volume.size = Vector2(312,30)
    volume.min_value = 0
    volume.max_value = 100
    volume.step = 5
    volume.value = 35
    panel.add_child(volume)
    alias_field = LineEdit.new()
    alias_field.name = "AliasField"
    alias_field.placeholder_text = "Optional local alias (not saved online)"
    alias_field.position = Vector2(24,159)
    alias_field.size = Vector2(312,38)
    panel.add_child(alias_field)
    resume_button = Button.new()
    resume_button.name = "ResumeButton"
    resume_button.text = "RESUME  /  ENTER"
    resume_button.position = Vector2(24,222)
    resume_button.size = Vector2(312,46)
    panel.add_child(resume_button)
    resume_button.pressed.connect(func(): set_menu(false))
    volume.focus_next = volume.get_path_to(alias_field)
    alias_field.focus_next = alias_field.get_path_to(resume_button)
    resume_button.focus_next = resume_button.get_path_to(volume)
    get_viewport().size_changed.connect(_layout)
    _layout()
    overlay.hide()

func _layout() -> void:
    panel.position = (get_viewport_rect().size - panel.size) / 2
    world.queue_redraw()

func set_menu(value: bool) -> void:
    menu_open = value
    overlay.visible = value
    get_tree().paused = value
    if value:
        resume_button.grab_focus()
    else:
        get_viewport().gui_release_focus()

func _input(event: InputEvent) -> void:
    if event is InputEventKey and event.keycode == KEY_ESCAPE and event.pressed and not event.echo:
        set_menu(not menu_open)
        get_viewport().set_input_as_handled()

func _process(_delta: float) -> void:
    hud.text = "INPUT HARBOUR · LOCAL PROTOTYPE\nShots: %d    Steps: %d\nWorld: click / Space to fire · Right to step\nPause: ESC · slider, text and keyboard still work" % [world.shots, world.steps]
