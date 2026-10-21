extends SceneTree

var app: Node
var checks: Array[Dictionary] = []

func _initialize() -> void:
    call_deferred("run")

func settle() -> void:
    await process_frame
    await process_frame

func record(name: String, passed: bool, observed: Dictionary) -> void:
    checks.append({"name": name, "pass": passed, "observed": observed})

func click(at: Vector2) -> void:
    var motion := InputEventMouseMotion.new()
    motion.position = at
    root.push_input(motion, true)
    for down in [true, false]:
        var event := InputEventMouseButton.new()
        event.position = at
        event.button_index = MOUSE_BUTTON_LEFT
        event.pressed = down
        root.push_input(event, true)
        await process_frame

func key(code: Key, unicode_value: int = 0, echo_value: bool = false) -> void:
    for down in [true, false]:
        var event := InputEventKey.new()
        event.keycode = code
        event.unicode = unicode_value
        event.pressed = down
        event.echo = echo_value if down else false
        root.push_input(event, true)
        await process_frame

func center(control: Control) -> Vector2:
    return control.get_global_rect().get_center()

func suite(size_value: Vector2i) -> void:
    root.size = size_value
    app = load("res://main.tscn").instantiate()
    root.add_child(app)
    await settle()
    var tag := "%dx%d/" % [size_value.x, size_value.y]
    await click(Vector2(size_value.x-60,size_value.y-60))
    record(tag+"world_click", app.world.shots == 1, {"shots":app.world.shots})
    await click(app.menu_button.global_position+Vector2(18,22))
    record(tag+"icon_opens_without_shot", app.menu_open and paused and app.world.shots == 1, {"open":app.menu_open,"shots":app.world.shots})
    var tick_before: int = app.world.ticks
    await create_timer(0.12, true).timeout
    record(tag+"world_ticks_pause", app.world.ticks == tick_before, {"before":tick_before,"after":app.world.ticks})
    await click(Vector2(5,5))
    record(tag+"backdrop_does_not_close", app.menu_open and app.world.shots == 1, {"open":app.menu_open,"shots":app.world.shots})
    await click(app.volume.global_position+Vector2(260,15))
    var changed: float = app.volume.value
    record(tag+"slider_works_paused", changed != 35 and paused, {"value":changed})
    var before_steps: int = app.world.steps
    await key(KEY_RIGHT)
    record(tag+"slider_key_not_world", app.world.steps == before_steps, {"steps":app.world.steps,"volume":app.volume.value})
    await click(center(app.alias_field))
    await key(KEY_X, 120)
    record(tag+"text_works_paused", app.alias_field.text == "x" and app.world.shots == 1, {"text":app.alias_field.text,"shots":app.world.shots})
    var remembered: float = app.volume.value
    await key(KEY_ESCAPE)
    record(tag+"escape_resumes", not app.menu_open and not paused and app.world.shots == 1, {"open":app.menu_open,"shots":app.world.shots})
    await key(KEY_RIGHT)
    record(tag+"world_key_restored", app.world.steps == before_steps+1, {"steps":app.world.steps})
    await key(KEY_SPACE,32)
    record(tag+"space_fire_restored", app.world.shots == 2, {"shots":app.world.shots})
    await key(KEY_ESCAPE)
    await key(KEY_ESCAPE,0,true)
    record(tag+"echo_not_toggle", app.menu_open and paused, {"open":app.menu_open})
    record(tag+"settings_persist", app.volume.value == remembered and app.alias_field.text == "x", {"volume":app.volume.value,"text":app.alias_field.text})
    await click(center(app.resume_button))
    record(tag+"resume_click_no_shot", not app.menu_open and not paused and app.world.shots == 2, {"open":app.menu_open,"shots":app.world.shots})
    await key(KEY_ESCAPE)
    await key(KEY_ENTER)
    record(tag+"enter_resume", not app.menu_open and not paused, {"open":app.menu_open})
    await click(Vector2(38,92))
    record(tag+"decorative_hud_not_fullscreen_block", app.world.shots == 3, {"shots":app.world.shots})
    app.queue_free()
    await settle()

func run() -> void:
    await suite(Vector2i(640,480))
    await suite(Vector2i(960,640))
    var passed := true
    for row in checks:
        passed = passed and row["pass"]
    print("GA002_EVIDENCE="+JSON.stringify({"engine":Engine.get_version_info().string,"checks":checks,"pass":passed,"scope":"Actual injected viewport events; not OS/physical-device, export or solver acceptance."}))
    quit(0 if passed else 2)
