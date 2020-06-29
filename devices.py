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
                 minimum_trigger, **kwargs):
        super().__init__(name, parent, connection, **kwargs)

        # The minimum high/low time of a pulse sufficient to trigger the
        # device
        self.minimum_trigger = minimum_trigger


class Trigger(Output):
    allowed_devices = [TriggerableDevice]


class ClockableDevice(Device):
    def __init__(self, name, parent, connection, clock_minimum_trigger,
                 clock_minimum_period, **kwargs):
        super().__init__(name, parent, connection, **kwargs)
        # The minimum high/low time of a clock pulse sufficient to trigger the
        # device to output:
        self.clock_minimum_trigger = clock_minimum_trigger

        # The shortest interval between clock ticks this device can receive:
        self.clock_minimum_period = clock_minimum_period


class ClockLine(Device):
    allowed_devices = [ClockableDevice]

    def __init__(self, name, parent, connection, **kwargs):
        super().__init__(name, parent, connection, **kwargs)

        self.clock_minimum_period = parent.clock_minimum_period
        self.timebase = parent.timebase

        # To be determined during establish_common_limits:
        self.common_clock_minimum_period = None
        self.common_clock_minimum_trigger = None
        self.clock_period_limiting_device = None
        self.clock_trigger_limiting_device = None

    def establish_common_limits(self):
        super().establish_common_limits()
        # How slow is the slowest ClockableDevice clocked by this ClockLine,
        # and which device is it, or are we the limiting device?
        self.common_clock_minimum_period = self.clock_minimum_period
        self.clock_period_limiting_device = self
        # What's the shortest clock trigger duration sufficient to clock all
        # ClockableDevice clocked by this pseudoclock, and which device needs
        # the longest one?
        self.common_clock_minimum_trigger = 0
        self.clock_trigger_limiting_device = None

        for device in self.descendant_devices(recurse_into_pseudoclocks=False):
            if isinstance(device, ClockableDevice):
                if device.clock_minimum_period > self.common_clock_minimum_period:
                    self.common_clock_minimum_period = device.clock_minimum_period
                    self.clock_period_limiting_device = device
                if device.clock_minimum_trigger > self.common_clock_minimum_trigger:
                    self.common_clock_minimum_trigger = device.clock_minimum_trigger
                    self.clock_trigger_limiting_device = device

        # Round up to multiple of the timebase:
        quantised = int(self.common_clock_minimum_period) + 1
        self.common_clock_minimum_period = quantised * self.timebase

        # We don't round self.common_clock_minimum_trigger to anything about
        # the timebase, as it is more about the duty cycle of the clocking
        # signals, whereas timebase is about the period of the clocking
        # signals. We don't know what the limits or quantisation on duty
        # cycles are. It's up to the pseudoclock's implementation to produce
        # triggers long enough or to raise an exception.


class Pseudoclock(Device):
    allowed_devices = [ClockLine]
    def __init__(self, name, parent, connection, clock_minimum_period, 
                 wait_delay, timebase, **kwargs):
        super().__init__(name, parent, connection, **kwargs)
        # The shortest clock period this device is capable of producing. This
        # is a float, and will be rounded to the nearest multiple of
        # `timebase`. If you have a device whose smallest clock period is not
        # a multiple of its timebase (say the clock intervals producable are c
        # + n * dt where dt is the timebase and c is some other time
        # duration), then this is not currently supported, please file a
        # feature request.
        self.clock_minimum_period = clock_minimum_period
           
        # The delay, upon executing a wait instruction, before the
        # pseudoclock will be responsive to a received trigger:
        self.wait_delay = wait_delay

        # Time resolution with which one can specify the period of a clock
        # tick.
        self.timebase = timebase

        self.pseudoclock = self


class PseudoclockDevice(TriggerableDevice):
    allowed_devices = [Pseudoclock]
    def __init__(self, name, parent, connection, **kwargs):
        super().__init__(name, parent, connection, **kwargs)
        # The time that this device will be triggered by its parent.
        # "None" means as early as possible:
        self.initial_trigger_time = None 

    def set_initial_trigger_time(self, initial_trigger_time):
        self.initial_trigger_time = initial_trigger_time
