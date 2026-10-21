extends RefCounted

func read_checkpoint() -> String:
    # Preserve the documented 4.3 default buffer size explicitly in 4.4.
    return OS.read_string_from_stdin().strip_edges()
