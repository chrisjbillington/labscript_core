from operator import attrgetter
from enum import IntEnum
from functools import wraps

class phase(IntEnum):
    """Enum for what 'phase' of compilation we are up to, to enforce certain
    methods only be called in certain phases"""

    # The following compilation steps happen in this order.

    DEFINE_CONNECTION_TABLE = 0
    ESTABLISH_COMMON_LIMITS = 1
    ESTABLISH_INITIAL_ATTRIBUTES = 2
    ADD_INSTRUCTIONS = 3
    CONVERT_TIMING = 4
    CHECK_INSTRUCTIONS_VALID = 5


def enforce_phase(phase):
    """Decorate an instance method to enforce that it only be called
    in a particular phase of the compilation process"""
    def decorator(method):
        @wraps(method)
        def check_phase(self, *args, **kwargs):
            try:
                shot = self.shot
            except AttributeError:
                # If it's an __init__ method then the shot attribute doesn't
                # exist yet - but the parent is the first argument after self
                # so we can get it there:
                shot = args[0].shot
            if shot.phase != phase:
                msg = (f"{self.__class__.__name__}.{method.__name__}() "
                       f"cannot be called in phase {shot.phase.name}")
                raise RuntimeError(msg)
            return method(self, *args, **kwargs)
        return check_phase
    return decorator


def sort_by_time(instructions):
    instructions.sort(key=attrgetter('t'))


def sorted_by_time(instructions):
    instructions = instructions.copy()
    sort_by_time(instructions)
    return instructions


def sort_by_quantised_time(instructions):
    instructions.sort(key=attrgetter('quantised_t'))


def sorted_by_quantised_time(instructions):
    instructions = instructions.copy()
    sort_by_quantised_time(instructions)
    return instructions


def _const(c):
    """Return a constant function"""
    def const(t):
        if isinstance(c, np.ndarray):
            return np.full_like(t, c, dtype=type(c))
        else:
            return c
    return const


def formatobj(obj, *attrs):
    """Format an object and some arguments for printing"""
    from bases import Device
    from shot import Shot
    result = obj.__class__.__name__ + "("
    for attr in attrs:
        value = getattr(obj, attr)
        if isinstance(value, Device) or isinstance(value, Shot):
            value = value.name
        result += f"{attr}={value}, "
    result = result[:-2] + ')'
    return result