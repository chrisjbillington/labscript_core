import numpy as np
import inspect
import traceback
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


class Instruction(object):
    def __init__(self, parent, t, *args, **kwargs):
        super().__init__(parent, t, *args, **kwargs)
        self.t = t

        # Timing details to be computed during processing:
        self.relative_t = None
        self.quantised_t = None

        # For giving the user a traceback if an error regarding this
        # instruction is found during later processing:
        self.traceback = self._get_traceback()

        # Count how many instructions there are and save which number we are:
        self.instruction_number = self.parent.shot.total_instructions
        self.parent.shot.total_instructions += 1

    def _convert_times(self, waits):
        """Convert all times specified by this instruction to ones relative to
        the start of our controlling pseudoclock, taking into account the
        effects of waits, and compute them as an integer in units of the
        pseudoclock's timebase. This method converts self.t, producing
        self.relative_t and self.quantised_t. Subclasses implementing this
        method should call our implementation, then convert any additional
        times that they specify to their relative and quantised versions."""
        pass

    def _get_traceback(self):
        """Get a traceback for the line of user code that created an
        instruction. Only meant to be called from the __init__ method of
        Instruction."""
        full_traceback_lines = traceback.format_stack()
        # how deep into the call stack are we from the function that the user
        # called to make this instruction?
        depth = 0
        for frame in inspect.getouterframes(inspect.currentframe()):
            depth += 1
            print(frame.frame.f_code)
            if frame.frame.f_code not in cls.instruction_code_objects:
                break
        return ''.join(full_traceback_lines[:-depth])

    def __str__(self):
        return _formatobj(self, 'parent', 't')


class Wait(Instruction):
    def __init__(self, parent, t, name, *args, **kwargs):
        super().__init__(parent, t, *args, **kwargs)
        self.name = name

    def __str__(self):
        return _formatobj(self, 'parent', 't', 'name')


class OutputInstruction(Instruction):
    """A class to distinguish non-wait instructions from wait instructions"""
    pass


class Function(OutputInstruction):
    """An instruction representing a function ramp"""
    def __init__(self, parent, t, duration, function, samplerate, *args, **kwargs):
        super().__init__(parent, t, *args, **kwargs)
        self.function = function
        self.parent = parent
        self.duration = duration
        self.samplerate = samplerate

        # Timing details to be computed during processing:
        self.quantised_duration = None
        self.quantised_samplerate = None

        # Results to be computed during processing:
        self.evaluation_timepoints = None
        self.values = None


    def _convert_times(self, waits):
        pass

    def __str__(self):
        return _formatobj(self, 'parent', 't', 'duration', 'function', 'samplerate')


class Constant(OutputInstruction):
    """An instruction for setting an output value at a specific time"""
    def __init__(self, parent, t, value, *args, **kwargs):
        # A constant instruction is just a function instruction with no
        # duration and a zero sample rate:
        super().__init__(parent, t, 0, _const(value), 0, *args, **kwargs)
        self.value = value

    def __str__(self):
        return _formatobj(self, 'parent', 't', 'value')


class HasInstructions(object):
    """Mixin for objects that have instructions, currently: Shot (which can
    have wait instructions) and Output (which can have all other
    instructions). Note that when inheriting both HasInstructions and
    HasDevices, inheriting HasInstructions first means that the
    all_instructions property will not recurse into child devices."""
    allowed_instructions = [Instruction]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instructions = []

    def add_instruction(self, instruction):
        if not any(isinstance(instruction, cls) for cls in self.allowed_instructions):
            raise TypeError(f"Instruction of type {device.__class__.__name__} not permitted " 
                            "by this instance.")
        self.instructions.append(instruction)

    @property
    def all_instructions(self):
        """Return our instructions. Do not recurse into child devices, in the
        case that we inherit from HasDevices as well"""
        return self.instructions

    def __repr__(self):
        return self.__str__()


class HasDevices(object):
    """Mixin for objects that have child devices, currently: Shot and
    Device."""
    # Will be interpreted as allowed_devices = [Device], but the name Device
    # is not available yet. Subclasses should override this class attribute to
    # specify which devices are allowed as children:
    allowed_devices = None
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.allowed_devices is None:
            self.allowed_devices = [Device]
        self.devices = []

    def add_device(self, device):
        if not any(isinstance(device, cls) for cls in self.allowed_devices):
            raise TypeError(f"Device of type {device.__class__.__name__} not permitted " 
                            "by this instance.")
        self.devices.append(child_device)

    @property
    def all_devices(self):
        """Recursively return all devices."""
        devices = self.devices.copy()
        for device in self.devices:
            devices.extend(device.all_devices)

    @property
    def all_instructions(self):
        """Recursively return instructions from all devices. Note that devices
        inheriting from HasInstructions before HasDevices will return only
        their instructions and not recurse into their own child devices. """
        instructions = []
        for device in self.devices:
            instructions.extend(device.all_instructions)
        return instructions

    def __repr__(self):
        return self.__str__()


class Device(HasDevices):
    # Will be interpreted as allowed_devices = [Device], but the name Device
    # is not available during class construction. Subclasses should override
    # this class attribute to specify which devices are allowed as children:
    allowed_devices = None
    def __init__(self, name, parent, connection, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.parent = parent
        self.connection = connection

    def delay(self, child):
        """The time elapsed between receiving a trigger/clock tick and
        providing output to a given child device or Instruction. Should be 
        zero for top level devices."""
        raise NotImplementedError("Subclasses must implement delay()")

    def __str__(self):
        return _formatobj(self, 'name', 'parent', 'connection')


class Output(HasInstructions, Device):
    allowed_instructions = [OutputInstruction]
    allowed_devices = [Device]
    def __init__(self, name, parent, connectionn, *args, **kwargs):
        super().__init__(self.allowed_instructions, name, parent, connection, *args, **kwargs)  
          
    def function(self, t, duration, function, samplerate):
        Function(self, t, duration, function, samplerate)
        return duration

    def constant(self, t, value):
        Constant(self, t, value)
        return 0


class TriggerableDevice(Device):
    def __init__(self, name, parent, connection,
                 minimum_trigger_duration, *args, **kwargs):
        super().__init__(name, parent, connection, *args, **kwargs)

        # The minimum high/low time of a pulse sufficient to trigger the
        # device
        self.minimum_trigger_duration = minimum_trigger_duration


class Trigger(Output):
    allowed_devices = [TriggerableDevice]


class ClockableDevice(Device):
    def __init__(self, name, parent, connection, minimum_trigger_duration, minimum_period,
                 *args, **kwargs):
        super().__init__(name, parent, connection, *args, **kwargs)
        # The minimum high/low time of a pulse sufficient to trigger the
        # device
        self.minimum_trigger_duration = minimum_trigger_duration

        # The shortest interval between outputs this device is capable of
        # producing, also equal to the shortest interval between clock ticks
        # it can receive
        self.minimum_period = minimum_period


class ClockLine(Device):
    allowed_devices = [ClockableDevice]


class Pseudoclock(Device):
    allowed_devices = [ClockLine]
    def __init__(self, name, parent, connection, minimum_period, 
                 minimum_wait_duration, timebase, *args, **kwargs):
        super().__init__(name, parent, connection, *args, **kwargs)
        # The shortest clock period this device is capable of producing
        self.minimum_period = minimum_period
           
        # The delay, upon executing a wait instruction, before the
        # pseudoclock will be responsive to a received trigger:
        self.minimum_wait_duration = minimum_wait_duration

        # Time resolution with which one can specify the period of a clock
        # tick
        self.timebase = timebase


class PseudoclockDevice(TriggerableDevice):
    allowed_devices = [Pseudoclock]
    def __init__(self, name, parent, connection, *args, **kwargs):
        super().__init__(name, parent, connection, *args, **kwargs)
        # The time that this device will be triggered by its parent.
        # "None" means as early as possible:
        self.initial_trigger_time = None 

    def set_initial_trigger_time(self, initial_trigger_time):
        self.initial_trigger_time = initial_trigger_time


class Shot(HasDevices, HasInstructions):
    """Top level object for the compilation"""
    allowed_instructions=[Wait]

    def __init__(self, name, epsilon, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.epsilon = epsilon
        self.name = name

    def start(self):
        # TODO up: add_device, min clock periods
        # down: delays
        # triggers
        pass

    def wait(self, t, name):
        Wait(self, t, name)
        # TODO: triggers

    def compile(self):

        _sort_by_time(self.waits)
        
        # TODO: Quantise and relativise times 
        # TODO Error check up. First on all instructions, then on parent devices upward one
        # layer at a time

        
        for pseudoclock in self.children:
            self.compile_pseudoclock(pseudoclock, waits)

    def _compile_pseudoclock(self, pseudoclock, waits):
        # Get all instructions on this pseudoclock:
        instructions = pseudoclock.get_instructions()

        # Process waits. 
        # Compute the time of each instruction relative to the start of its
        # pseudoclock:
        for inst in instructions:
            print(inst)


    # TODO: all this inheritance business:
    # if isinstance(self.parent_device, Shot):
    #     self.shot = parent_device
    #     self.t0 = 0
    #     self.wait_prep_duration = self.minimum_wait_duration
    # else:
    #     self.shot = parent.shot
    #     self.t0 = parent.t0 + parent.trigger_delay(self)
    #     self.wait_prep_duration = self.minimum_wait_duration + shot.epsilon - self.t0

    # if isinstance(self, Pseudoclock):
    #     self.pseudoclock = self
    # else:
    #     self.pseudoclock = parent.pseudoclock


    def __str__(self):
        return _formatobj(self, 'name')



shot = Shot('<shot>', 100e-9)
pulseblaster = PseudoclockDevice('pulseblaster', shot, None, minimum_trigger_duration=0.1)
pulseblaster_clock = Pseudoclock('pulseblaster_clock', pulseblaster, 'clock',
                                 minimum_period=1, minimum_wait_duration=0.5, timebase=0.1)
clockline = ClockLine('clockline', pulseblaster_clock, 'flag 1')
# pseudoclock = Pseudoclock('pseudoclock', shot, None, minimum_period=1,
                           # minimum_wait_duration=0.5, timebase=0.1)

# ni_card = Clocl