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
    def __init__(self, parent, t, *args, _inst_depth=1, **kwargs):
        """Base instruction class. Has an initial time, and that's about it.
        __inst_depth is the stack depth of functions that are wrappers around
        instantiating Instructions. All such functions (including the __init__
        method of subclasses of Instruction) should accept an _inst_depth=1
        keyword argument, and should pass inst_depth=_inst_depth+1 to the
        function they are wrapping (or the __init__ method of the Instruction
        class they are subclassing), in order for the traceback-making code to
        figure out where in the stack user code ends and labscript code
        begins. This is so that we can raise tracebacks that end at the line
        of user code that resulted in creating the instruction (internal
        labscript tracebacks, unless labscript itself has crashed, are not
        useful)."""
        super().__init__(*args, **kwargs)
        self.parent = parent
        self.t = t
        self.parent.add_instruction(self)
        self.shot = parent.shot
        self.pseudoclock = parent.pseudoclock

        # Timing details to be computed during processing:
        self.relative_t = None
        self.quantised_t = None

        # For giving the user a traceback if an error regarding this
        # instruction is found during later processing:
        self.traceback = ''.join(traceback.format_stack()[:-_inst_depth])

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

    def __str__(self):
        return _formatobj(self, 'parent', 't')

    def __repr__(self):
        return self.__str__()


class Wait(Instruction):
    def __init__(self, parent, t, name, *args, _inst_depth=1, **kwargs):
        super().__init__(parent, t, *args, _inst_depth=_inst_depth+1, **kwargs)
        self.name = name

    def __str__(self):
        return _formatobj(self, 'parent', 't', 'name')


class OutputInstruction(Instruction):
    """A class to distinguish non-wait instructions from wait instructions"""
    pass


class Function(OutputInstruction):
    """An instruction representing a function ramp"""
    def __init__(self, parent, t, duration, function, samplerate,
                 *args, _inst_depth=1, **kwargs):
        super().__init__(parent, t, *args, _inst_depth=_inst_depth+1, **kwargs)
        self.function = function
        self.parent = parent
        self.duration = duration
        self.samplerate = samplerate

        # Timing details to be computed during processing:
        self.quantised_duration = None
        self.quantised_sample_period = None

        # Results to be computed during processing:
        self.evaluation_timepoints = None
        self.values = None


    def _convert_times(self, waits):
        pass

    def __str__(self):
        return _formatobj(self, 'parent', 't', 'duration', 'function', 'samplerate')


class Constant(Function):
    """An instruction for setting an output value at a specific time"""
    def __init__(self, parent, t, value, *args, _inst_depth=1, **kwargs):
        # A constant instruction is just a function instruction with no
        # duration and a zero sample rate:
        super().__init__(parent, t, 0, _const(value), 0,
                         *args, _inst_depth=_inst_depth+1, **kwargs)
        self.value = value

    def __str__(self):
        return _formatobj(self, 'parent', 't', 'value')


class Static(OutputInstruction):
    """An instruction for setting an unchanging output's value for the
    duration of the experiment"""
    def __init__(self, parent, value, *args, _inst_depth=1, **kwargs):
        # A static instruction has t=0:
        super().__init__(parent, 0, *args, _inst_depth=_inst_depth+1, **kwargs)

    def __str__(self):
        return _formatobj(self, 'parent', 'value')


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
                            f"by {self}.")
        self.instructions.append(instruction)

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
                            f"as child of {self}.")
        self.devices.append(device)

    def descendant_devices(self, recurse_into_pseudoclocks=False):
        """Recursively return devices that are descendants of this instance
        (not including this instance itself). If recurse_into_pseudoclocks is
        True, then pseudoclocks that are descendants of this instance, and all
        of their descendants (including further pseudoclocks and so on) will
        be returned as well, otherwise they will be excluded."""
        devices = []
        for device in self.devices:
            if isinstance(device, Pseudoclock) or not recurse_into_pseudoclocks:
                continue
            else:
                devices.append(device)
                devices.extend(device.descendant_devices(recurse_into_pseudoclocks))

    def descendant_instructions(self, recurse_into_pseudoclocks=False):
        """Recursively return instructions of all devices that are descendants
        of this instance, including its own instructions (if any). If
        recurse_into_pseudoclocks is True, then instructions of pseudoclocks
        that are descendants of this instance, and all of their descendants
        (including further pseudoclocks and so one) will be returned as well,
        otherwise they will be excluded."""
        if isinstance(self, HasInstructions):
            instructions = self.instructions.copy()
        else:
            instructions = []
        for device in self.devices:
            if isinstance(device, Pseudoclock) or not recurse_into_pseudoclocks:
                continue
            else:
                instructions.extend(device.descendant_instructions(recurse_into_pseudoclocks))

    def __repr__(self):
        return self.__str__()


class Device(HasDevices):
    # allowed_devices = None will be interpreted as allowed_devices =
    # [Device], but the name Device is not available during class
    # construction. Subclasses should override this class attribute to specify
    # which devices are allowed as children:
    allowed_devices = None
    output_delay = 0

    def __init__(self, name, parent, connection, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.parent = parent
        self.connection = connection
        self.parent.add_device(self)
        self.shot = self.parent.shot
        self.pseudoclock = self.parent.pseudoclock

    def get_output_delay(self, child):
        """The time elapsed between receiving a trigger/clock tick and
        providing output to a given child device or Instruction. Should be
        zero for top level devices. Subclasses should either set a class or
        instance attribute if delays are constant, or should reimplement this
        function if delays depend on the child device or instruction"""
        return self.output_delay

    def __str__(self):
        return _formatobj(self, 'name', 'parent', 'connection')


class StaticDevice(Device):
    """A class whose outputs don't change during the experiment, and hence
    which requires no clocking signal or trigger"""
    pass


class Output(Device, HasInstructions):
    allowed_instructions = [OutputInstruction]
    allowed_devices = [Device]
    def __init__(self, name, parent, connection, *args, **kwargs):
        super().__init__(name, parent, connection, *args, **kwargs)  
          
    def function(self, t, duration, function, samplerate, _inst_depth=1):
        Function(self, t, duration, function, samplerate, _inst_depth=_inst_depth+1)
        return duration

    def constant(self, t, value, _inst_depth=1):
        Constant(self, t, value, _inst_depth=_inst_depth+1)
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

        self.pseudoclock = self


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
    allowed_instructions = [Wait]
    allowed_devices = [PseudoclockDevice, StaticDevice]

    def __init__(self, name, epsilon, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.epsilon = epsilon
        self.name = name
        self.master_pseudoclock = None
        self.total_instructions = 0

        # For our child devices looking to inherit shot and pseudoclock from
        # their parent:
        self.shot = self
        self.pseudoclock = None

    def add_device(self, device):
        if isinstance(device, PseudoclockDevice):
            if self.master_pseudoclock is not None:
                raise ValueError(f"Cannot add second master pseudoclock '{device.name}'. "
                                 f"Already have master pseudoclock '{self.master_pseudoclock.name}'")
            self.master_pseudoclock = device
        super().add_device(device)


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



if __name__ == '__main__':
    shot = Shot('<shot>', 100e-9)
    pulseblaster = PseudoclockDevice('pulseblaster', shot, None, minimum_trigger_duration=0.1)
    pulseblaster_clock = Pseudoclock('pulseblaster_clock', pulseblaster, 'clock',
                                     minimum_period=1, minimum_wait_duration=0.5, timebase=0.1)
    clockline = ClockLine('clockline', pulseblaster_clock, 'flag 1')
    ni_card = ClockableDevice('ni_card', clockline, 'clock', minimum_trigger_duration=0.1, minimum_period=1.2)
    ao = Output('ao', ni_card, 'ao0')
    ao.constant(t=0, value=7)
    ao.function(t=0, duration=7, function=np.sin, samplerate=20)
    shot.wait(t=7, name='first_wait')

# Compilation steps:
# collect_descendant_limitations
# pass_down_delays
    # pseudoclock.child_