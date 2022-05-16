def generate_trigger_function(sensors: dict, merged=False):
    keys = [key for key in sensors.keys()]

    if len(keys) == 1:
        return lambda: sensors[keys[0]][1][0](sensors[keys[0]][0](), sensors[keys[0]][2]), None

    if merged:
        if len(keys) == 3:
            return lambda: (sensors[keys[0]][1][0](sensors[keys[0]][0](), sensors[keys[0]][2]) and
                            sensors[keys[1]][1][0](sensors[keys[1]][0](), sensors[keys[1]][2]) and
                            sensors[keys[2]][1][0](sensors[keys[2]][0](), sensors[keys[2]][2]))

        else:
            return lambda: (sensors[keys[0]][1][0](sensors[keys[0]][0](), sensors[keys[0]][2]) and
                            sensors[keys[1]][1][0](sensors[keys[1]][0](), sensors[keys[1]][2]))

    else:
        if len(keys) == 3:
            return lambda: sensors[keys[0]][1][0](sensors[keys[0]][0](), sensors[keys[0]][2]), \
                   lambda: sensors[keys[1]][1][0](sensors[keys[1]][0](), sensors[keys[1]][2]), \
                   lambda: sensors[keys[2]][1][0](sensors[keys[2]][0](), sensors[keys[2]][2])
        else:
            return lambda: sensors[keys[0]][1][0](sensors[keys[0]][0](), sensors[keys[0]][2]), \
                   lambda: sensors[keys[1]][1][0](sensors[keys[1]][0](), sensors[keys[1]][2])
