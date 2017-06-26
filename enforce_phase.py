import weakref
from enum import IntEnum
from functools import wraps

# Determines whether the enforce_phase decorator has any effect. Useful to set
# to False when not debugging or developing, to ensure there is no adverse
# performance hit from checking every method call.
ENFORCE_PHASE = False


# Exception classes for when the phase enforcement detects a problem:
class PhaseError(RuntimeError):
    pass

class WrongPhaseError(PhaseError):
    pass

class AlreadyCalledError(PhaseError):
    pass

class NotCalledError(PhaseError):
    pass

class phase(IntEnum):
    """Enum for what 'phase' of compilation we are up to, to enforce that
    certain methods only be called in certain phases"""

    # The following compilation steps happen in this order.

    ADD_DEVICES = 0
    ESTABLISH_COMMON_LIMITS = 1
    ESTABLISH_INITIAL_ATTRIBUTES = 2
    ADD_INSTRUCTIONS = 3
    CONVERT_TIMING = 4
    CHECK_INSTRUCTIONS_VALID = 5


class has_phase_enforced_methods(type):
    """metaclass to allow methods decorated with @enforce_phase to know what
    class they were being defined on (this information is not available during
    class definition at which point methods are just ordinary functions). This
    is necessary for us to be able to check later that methods that need to be
    called have been called on every instance that has them. bases.HasParent,
    and therefore basically every object in labscript.core use this as their
    metaclass"""
    def __init__(cls, name, superclasses, attrs):
        # Create the class as usual:
        type.__init__(cls, name, superclasses, attrs)
        # Inspect the class for methods that have been decorated with
        # @enforce_phase and marked as methods that must be called exactly
        # once in their phase:
        for name, attr in cls.__dict__.items():
            if getattr(attr, 'is_phase_enforced_method', False) and attr.exactly_once:
                # Add the decorated method to the  registry of decorated
                # methods that are required to be called exactly once
                enforce_phase.register_required_method(cls, attr)


class enforce_phase(object):
    """Decorate an instance method to enforce that it only be called in a
    particular phase of the compilation process, and if required, that it
    be called exactly once during that phase """

    # Class attribute to store a list of objects by what shot they belong to,
    # so that we can do checks on all the descendants of a shot when its phase
    # changes. WeakKeyDictionary so that it vanishes when the shot does. All
    # subclasses will access this same mutable attribute:
    instances_by_shot = weakref.WeakKeyDictionary()

    # Set of methods of each class that are required to be called exactly once
    # on each instance during a given phase. Format: {phase: {class:
    # set(method, other_method, ...)}).
    required_methods = {}

    # Store methods that have been called on a given instance. Format:
    # {instance: set([methods])}
    called_methods = weakref.WeakKeyDictionary()

    def __init__(self, phase, exactly_once=False):
        self.phase = phase
        self.exactly_once = exactly_once

    def __call__(self, method):
        if not ENFORCE_PHASE:
            return method
        if self.exactly_once and method.__name__ == '__init__':
            msg = "No need to set exactly_once=True on an __init__ method"
            raise ValueError(msg)

        @wraps(method)
        def check_phase(instance, *args, **kwargs):
            try:
                shot = instance.shot
            except AttributeError:
                # If it's an __init__ method then the parent is one of the
                # arguments:
                from bases import Device, Instruction
                if isinstance(instance, Device):
                    shot = args[1].shot
                elif isinstance(instance, Instruction):      
                    shot = args[0].shot
                else:
                    msg = (f"enforce_phase doesn't know "
                           f"about classes of type {instance.__class__.__name__}")
                    raise TypeError(msg)
            if shot.phase != self.phase:
                msg = (f"{instance.__class__.__name__}.{method.__name__}() "
                       f"cannot be called in phase {shot.phase.name}")
                raise WrongPhaseError(msg)
            if self.exactly_once:
                called = enforce_phase.called_methods.setdefault(instance, set())
                if method in called:
                    msg = (f"{instance} has already had {method.__name__}() "
                           f"called once in phase {shot.phase.name}")
                    raise AlreadyCalledError(msg)
                called.add(method)
            return method(instance, *args, **kwargs)

        check_phase.is_phase_enforced_method = True
        check_phase.exactly_once = self.exactly_once
        check_phase.phase = self.phase
        check_phase.method = method

        return check_phase

    @classmethod
    def register_instance(cls, instance):
        """Add an instance to our registry of all instances that are
        descendants of each shot"""
        descendents_of_shot = cls.instances_by_shot.setdefault(instance.shot, set())
        descendents_of_shot.add(instance)

    @classmethod
    def register_required_method(cls, meth_cls, phase_enforced_method):
        """Register that a method of a class can only be called in a
        particular phase, and optionally that it needs to be called exactly
        once in its phase"""
        method = phase_enforced_method.method
        phase = phase_enforced_method.phase
        methods = cls.required_methods.setdefault(phase, {}).setdefault(meth_cls, set())
        methods.add(method)

    @classmethod
    def check_required_methods_called(cls, shot, phase):
        """Confirm that at the end of given phase, all methods that were
        marked as needing to be called exactly once were called on every
        instance"""
        if not ENFORCE_PHASE:
            return
        for instance in cls.instances_by_shot[shot]:
            required_methods_by_class = cls.required_methods.get(phase, {})
            for class_, required_methods in required_methods_by_class.items():
                if isinstance(instance, class_):
                    called_methods = cls.called_methods.get(instance, set())
                    for method in (required_methods - called_methods):
                        # Just raise an exception about one of the required
                        # but uncalled methods:
                        msg = (f"{instance} has not had {method.__name__}() "
                               f"called by the end of phase {phase.name}")
                        raise NotCalledError(msg)

