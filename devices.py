from bases import Device, Output
from instructions import Static


class StaticDevice(Device):
    """A class whose outputs don't change during the experiment, and hence
    which requires no clocking signal or trigger"""
    pass


class StaticOutput(Output):
    """Output that only allows static instructions"""
    allowed_instructions = [Static]


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