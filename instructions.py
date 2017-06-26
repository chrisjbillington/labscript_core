from bases import Instruction, OutputInstruction
from utils import _const, formatobj

class Wait(Instruction):
    def __init__(self, parent, t, name, _inst_depth=1, **kwargs):
        super().__init__(parent, t, _inst_depth=_inst_depth+1, **kwargs)
        self.name = name

    def __str__(self):
        return formatobj(self, 'parent', 't', 'name')


class Function(OutputInstruction):
    """An instruction representing a function ramp"""
    def __init__(self, parent, t, duration, function, samplerate,
                 _inst_depth=1, **kwargs):
        super().__init__(parent, t, _inst_depth=_inst_depth+1, **kwargs)
        self.function = function
        self.duration = duration
        self.samplerate = samplerate

        # Timing details to be computed during processing:
        self.quantised_duration = None
        self.quantised_sample_period = None

        # Results to be computed during processing:
        self.evaluation_timepoints = None
        self.values = None


    def convert_timing(self, waits):
        super().convert_timing( waits)
        pass

    def __str__(self):
        return formatobj(self, 'parent', 't', 'duration', 'function', 'samplerate')


class Constant(Function):
    """An instruction for setting an output value at a specific time"""
    def __init__(self, parent, t, value, _inst_depth=1, **kwargs):
        # A constant instruction is just a function instruction with no
        # duration and a zero sample rate:
        super().__init__(parent, t, 0, _const(value), 0,
                         _inst_depth=_inst_depth+1, **kwargs)
        self.value = value

    def __str__(self):
        return formatobj(self, 'parent', 't', 'value')


class Static(OutputInstruction):
    """An instruction for setting an unchanging output's value for the
    duration of the experiment"""
    def __init__(self, parent, value, _inst_depth=1, **kwargs):
        # A static instruction has t=0:
        super().__init__(parent, 0, _inst_depth=_inst_depth+1, **kwargs)

    def __str__(self):
        return formatobj(self, 'parent', 'value')
