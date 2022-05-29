def generate_trigger_function(params: tuple, testing=False):
    if testing:
        return lambda: params[1](float(params[0]()), params[3])
    return lambda: params[1](params[0](), params[3])






