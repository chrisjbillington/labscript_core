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


def _formatobj(obj, *args, **kwargs):
    """Format an object and some arguments for printing"""
    result = obj.__class__.__name__ + "("
    for arg in args:
        result += f"{arg, }"
    for kwarg, value in kwargs.items():
        if isinstance(value, Child) or isinstance(value, Shot):
            value = value.name
        result += f"{kwarg}={value}, "
    result = result[:-2] + ')'
    return result


class Shot(object):
    """Top level object for the compilation"""
    def __init__(self, epsilon):
        self.epsilon = epsilon
        self.child_devices = []
        self.instructions = []
        self.name = '<shot>'
        self.total_instructions = 0
        self.master_pseudoclock = None

    def _add_child_device(self, child_device):
        self.children.append(child_device)
        if isinstance(child_device, PseudoclockDevice):
            if self.master_pseudoclock is not None:
                raise ValueError(f"Already have a master pseudoclock: {self.master_pseudoclock}. "
                                 "Cannot set two pseudoclock devices as child devices of the shot")
            self.master_pseudoclock = child_device

    def _add_instruction(self, instruction):
        self.waits.append(instruction)

    def _get_child_devices(self):
        """Return all children recursively from child devices connected to
        this device"""
        child_devices = self.child_devices.copy()
        for child_device in self.child_devices:
            child_devices.extend(child_device.get_child_devices())
        return instructions

    def start(self):
        #TODO: tell all devices to inherit everything:
        return self.wait(0)

    def wait(self):
        # TODO: triggers:
        Wait(self, t)


    def compile(self):
        # First we ensure our wait instructions are ordered by time:
        _sort_by_time(self.waits)
        
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


class Child(object):
    """A parent class for both devices and instructions"""
    def __init__(self, name, parent_device):
        self.name = name
        self.parent_device = parent_device
        self.parent_device.add_child_device(self)

        if isinstance(self.parent_device, Shot):
            self.shot = parent_device
            self.t0 = 0
            self.wait_prep_duration = self.minimum_wait_duration
        else:
            self.shot = parent.shot
            self.t0 = parent.t0 + parent.trigger_delay(self)
            self.wait_prep_duration = self.minimum_wait_duration + shot.epsilon - self.t0

        if isinstance(self, Pseudoclock):
            self.pseudoclock = self
        else:
            self.pseudoclock = parent.pseudoclock

    def __str__(self):
        return _formatobj(self, name=self.name, parent=self.parent)

    __repr__ = __str__


class Device(Child):

    def __init__(self, name, parent, connection):
        super().__init__(name, parent)
        self.connection = connection
        self.children = []

    def _add_child(self, child):
        self.children.append(child)

    def get_instructions(self):
        """Return all instructions recursively from child devices connected to
        this device"""
        instructions = []
        for child in self.children:
            instructions.extend(child.get_instructions())
        return instructions

    def get_children(self):
        """Return all children recursively from child devices connected to
        this device"""
        children = self.children.copy()
        for child in self.children:
            children.extend(child.children())
        return instructions

    def trigger_delay(self, child):
        """The time elapsed between receiving a trigger/clock tick and
        providing output to a given child device or Instruction"""
        if self.parent is self.shot:
            # Master pseudoclock has no trigger delay.
            return 0
        raise NotImplementedError("Subclasses must implement trigger_delay() to specify "
                                  "the delay between input and output to a specific child")

    def __str__(self):
        return _formatobj(self, name=self.name, parent=self.parent,
                          connection=self.connection)


class TriggerableDevice(Device):
    def __init__(self, name, parent, connection, minimum_trigger_duration):
        super().__init__(name, parent, connection)
        # The minimum high/low time of a pulse sufficient to trigger the
        # device
        self.minimum_trigger_duration = minimum_trigger_duration


class PseudoclockDevice(TriggerableDevice):
    def __init__(self, name, parent, connection, minimum_trigger_duration):
        super().__init__(name, parent, connection, minimum_trigger_duration)

        
    
class Pseudoclock(Device):
    def __init__(self, name, parent, connection, minimum_period,
                 minimum_wait_duration, timebase):
        super().__init__(name, parent, connection)
        # The shortest clock period this device is capable of producing
        self.minimum_period = minimum_period
           
        # The delay, upon executing a wait instruction, before the
        # pseudoclock will be responsive to a received trigger:
        self.minimum_wait_duration = minimum_wait_duration

        # Time resolution with which one can specify the period of a clock
        # tick
        self.timebase = timebase


class ClockedDevice(Device):
    def __init__(self, name, parent, connection, minimum_trigger_duration, minimum_period):
        super().__init__(name, parent, connection)
        # The minimum high/low time of a pulse sufficient to trigger the
        # device
        self.minimum_trigger_duration = minimum_trigger_duration

        # The shortest interval between outputs this device is capable of
        # producing, also equal to the shortest interval between clock ticks
        # it can receive
        self.minimum_period = minimum_period


class Output(Device):
    def __init__(self, name, parent, connection):
        super().__init__(name, parent, connection)
        self.instructions = []

    def _add_child(self, child):
        if isinstance(child, Instruction):
            self.instructions.append(child)
        else:
            self.children.append(child)

    def get_instructions(self):
        """Return all instructions of this output"""
        return self.instructions

    def function(self, t, duration, function, samplerate):
        Function(self, t, duration, function, samplerate)
        return duration

    def constant(self, t, value):
        Constant(self, t, value)
        return 0


class Instruction(Child):

    def __init__(self, parent, t):
        super().__init__(None, parent)
        self.t = t

        # Timing details to be computed during processing:
        self.relative_t = None
        self.quantised_t = None

        # For giving the user a traceback if an error regarding this
        # instruction is found during later processing:
        self.traceback = self._get_traceback()

        # Count how many instructions there are and save which number we are:
        self.instruction_number = self.shot.total_instructions
        self.shot.total_instructions += 1

    def _convert_times(self, waits):
        """Convert all times specified by this instruction to ones relative to
        the start of our controlling pseudoclock, taking into account the
        effects of waits, and compute them as an integer in units of the
        pseudoclock's timebase. This method converts self.t, producing
        self.relative_t and self.quantised_t. Subclasses implementing this
        method should call our implementation, then convert any additional
        times that they specify to their relative and quantised versions."""
        import IPython
        IPython.embed()

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
        return _formatobj(self, parent=self.parent, t=self.t)


class Wait(Instruction):
    def __init__(self, parent, t, name):
        super().__init__(parent, t)
        self.name = name

    def __str__(self):
        return _formatobj(self, parent=self.parent, t=self.t, name=self.name)


class Function(Instruction):
    def __init__(self, parent, t, duration, function, samplerate):
        super().__init__(parent, t)
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
        return _formatobj(self, parent=self.parent, t=self.t, duration=self.duration,
                          function=self.function, samplerate=self.samplerate)


class Constant(Function):
    def __init__(self, parent, t, value):
        super().__init__(parent, t, 0, _const(value), 0)
        self.value = value

    def __str__(self):
        return _formatobj(self, parent=self.parent, t=self.t, value=self.value)




if __name__ == '__main__':

    import numpy as np

    shot = Shot(1)
    pseudoclock = Pseudoclock('pseudoclock', shot, None)
    ni_card = ClockedDevice('ni_card', pseudoclock, 'flag 1')
    ao = Output('ao', ni_card, 'ao0')

    ao.function(t=0, duration=10, function=np.sin, samplerate=20)
    ao.constant(t=4.25, value=7)

    print(ao.get_instructions()[0].traceback)


    shot.compile()