from operator import attrgetter


def _sort_by_time(instructions):
    instructions.sort(key=attrgetter('t'))


def _sorted_by_time(instructions):
    instructions = instructions.copy()
    _sort_by_time(instructions)
    return instructions


def _sort_by_quantised_time(instructions):
    instructions.sort(key=attrgetter('quantised_t'))


def _sorted_by_quantised_time(instructions):
    instructions = instructions.copy()
    _sort_by_quantised_time(instructions)
    return instructions


def _const(c):
    """Return a constant function"""
    def const(t):
        if isinstance(c, np.ndarray):
            return np.full_like(t, c, dtype=type(c))
        else:
            return c
    return const


def _formatobj(obj, *attrs):
    """Format an object and some arguments for printing"""
    result = obj.__class__.__name__ + "("
    for attr in attrs:
        value = getattr(obj, attr)
        if isinstance(value, Device) or isinstance(value, Shot):
            value = value.name
        result += f"{attr}={value}, "
    result = result[:-2] + ')'
    return result