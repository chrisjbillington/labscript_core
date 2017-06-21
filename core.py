import traceback


def _constantfunc(c):
    from numpy.polynomial import Polynomial
    return Polynomial([c])


def _formatobj(obj, *args, **kwargs):
    result = obj.__class__.__name__ + "("
    for arg in args:
        result += f"{arg, }"
    for kwarg, value in kwargs.items():
        result += f"{kwarg}={value}, "
    result = result[:-2] + ')'
    return result


class Compiler(object):
    def __init__(self):
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def compile(self):
        for pseudoclock in self.children:
            do_magic(pseudoclock)


class Child(object):
    def __init__(self, name, parent, connection):
        self.name = name
        self.parent = parent
        self.connection = connection
        if isinstance(parent, Compiler):
            self.is_master_pseudoclock = True
            self.compiler = parent
        else:
            self.parent.add_child(self)
            self.compiler = parent.compiler

    def __str__(self):
        return _formatobj(self, name=self.name,
                          parent=f"'{self.parent.name}'", connection=self.connection)

    __repr__ = __str__


class Device(Child):

    def __init__(self, name, parent, connection):
        super().__init__(name, parent, connection)
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def get_instructions(self):
        """Return all instructions recursively from child devices connected to
        this device"""
        instructions = []
        for child in self.children:
            instructions.extend(child.get_instructions())
        return instructions

    def trigger_delay(self, child):
        """The time elapsed between receiving a trigger/clock tick and
        providing output to a given child device"""
        if self.parent is None:
            return 0
        raise NotImplementedError("Subclasses must implement trigger_delay() to specify "
                                  "the delay between input and output to a specific child")

    def to_relative_time(self, t, wait_times):
        if self.parent is None:
            return t
            return _constantfunc(0)(t)
        return self.parent.to_relative_time(t - self.trigger_delay)


class Pseudoclock(Device):

    # Time resolution with which one can specify the period of a clock
    # tick
    timebase = None
        
    # The shortest clock period this device is capable of producing
    minimum_period = None
       
    # The delay, upon executing a wait instruction, before the
    # pseudoclock will be responsive to a received trigger
    minimum_wait_duration = None
        
    
class ClockedDevice(Device):

    # The minimum high/low time of a pulse sufficient to trigger the
    # device
    minimum_trigger_duration = None


class Output(Device):

    def get_instructions(self):
        """Return all instructions of this output"""
        return self.children


class Instruction(Device):
    def __init__(self):
        pass


class Ramp(Instruction):
    def __init__(self, t, duration, function, samplerate, parent, _traceback_depth=-1):
        super().__init__()
        self.t = t
        self.function = function
        self.parent = parent
        self.duration = duration
        self.samplerate = samplerate
        self.parent.add_child(self)

        # For giving the user a traceback if an error regarding this
        # instruction is found during later processing:
        self.traceback = ''.join(traceback.format_stack()[:_traceback_depth])

        # Timing details be computed during processing:
        self.relative_t = None
        self.quantised_t = None
        self.quantised_duration = None
        self.quantised_samplerate = None

        # Results to be computed during processing:
        self.evaluation_timepoints = None
        self.values = None


    def compute_timing(self, wait):
        """Called by the compiler during processing."""
        pass

    def __str__(self):
        return _formatobj(self, t=self.t, duration=self.duration, function=self.function,
                          samplerate=self.samplerate, parent=f"'{self.parent.name}'")



class Constant(Ramp):
    def __init__(self, t, value, parent):
        self.value = value
        super().__init__(t, duration=0, function=_constantfunc(value),
                         samplerate=0, parent=parent, _traceback_depth=-2)

    def __str__(self):
        return _formatobj(self, t=self.t, value=self.value, parent=f"'{self.parent.name}'")



def get_instructions(device):
    """Get all instructions from all outputs that are a child of a device"""
    if isinstance(device, Output):
        return device.children
    instructions = []
    for child in device.children:
        instructions.extend(get_instructions(child))
    return instructions


def do_magic(pseudoclock):
    # Get all instructions on this pseudoclock:
    instructions = pseudoclock.get_instructions()

    # Process waits. 
    # Compute the time of each instruction relative to the start of its
    # pseudoclock:
    for inst in instructions:
        print(inst)


if __name__ == '__main__':

    import numpy as np

    compiler = Compiler()
    pseudoclock = Pseudoclock('pseudoclock', compiler, None)
    ni_card = ClockedDevice('ni_card', pseudoclock, 'flag 1')
    ao = Output('ao', ni_card, 'ao0')

    instruction1 = Ramp(t=0, function=np.sin, parent=ao, duration=10, samplerate=20)
    instruction2 = Constant(t=4.25, value=7, parent=ao)

    do_magic(pseudoclock)