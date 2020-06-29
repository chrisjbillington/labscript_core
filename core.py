import numpy as np

from bases import Instruction, Device, Output

from instructions import Wait, OutputInstruction, Function, Constant, Static

from devices import (StaticDevice, StaticOutput, TriggerableDevice, Trigger, ClockableDevice,
                     ClockLine, Pseudoclock, PseudoclockDevice)

from shot import Shot


if __name__ == '__main__':
    import time
    start_time = time.time()
    shot = Shot('<shot>', 100e-9)
    pulseblaster = PseudoclockDevice('pulseblaster', shot, None, minimum_trigger=0.1)
    pulseblaster_clock = Pseudoclock('pulseblaster_clock', pulseblaster, 'clock',
                                     clock_minimum_period=1, wait_delay=0.5, timebase=0.1)
    clockline = ClockLine('clockline', pulseblaster_clock, 'flag 1')
    ni_card = ClockableDevice('ni_card', clockline, 'clock', clock_minimum_trigger=0.1, clock_minimum_period=1.2)
    ao = Output('ao', ni_card, 'ao0')
    shot.start()
    shot.wait(t=7, name='first_wait')
    ao.constant(t=0, value=7)
    ao.function(t=0, duration=7, function=np.sin, samplerate=20)

    shot.stop(1)

    print(time.time() - start_time)
    
# TODO list:
# If higher level labscript code subclasses or adds extra parent classes to
# Device/Output/Instruction etc, then those classes need to cooperate with
# this - calling super().__init__ methods etc, and we need to add settings
# (class attributes for subclasses to override?) to Shot that allow higher
# level code to replace the core library's base classes for Device etc with
# its own.

# Timing variable names:
#   latency:                            float or dict-->float by connection, or dict-->float by instruction class, giving this device's contribution to latency to that child
#   get_latency:                        method returning the above for a given child device or instruction, or with no args if latency is a float
#   ancestor_latency:                   float. latency including all parents up to the master pseudoclock (not including own latency)
#   minimum_trigger:                    float. minimum trigger required by TriggerableDevice
#   clock_minimum_trigger               float: minimum trigger required by ClockableDevice
#   common_minimum_trigger:             float: min trigger duration that satisfies all devices under this pseudoclock (rounded up to timebase)
#   common_clock_minimum_trigger        float: minimum trigger required by ClockableDevice
#   wait_delay:                         float: how long a pseudoclock waits at minimum
#   nominal_wait_delay:                 float: property of shot: the wait delay that satisfies all devices
#   prewait_overtime                    float: how long a device can still issue instructions after a call to wait() before the wait occurs for it.
#   clock_minimum_period:               float: shortest clock tick a PseudoClock can make or a ClockedDevice can receive
#   common_clock_minimum_period:        float: shortest clock tick all devices under this pseudoclock can deal with (or int? quantised and rounded up?)
#   t0:                                 method returning float: initial trigger time + ancestor_latency + get_latency(device_or_instruction)
#   postwait_t0:                        method returning float: ancestor_latency + get_latency(device_or_instruction)
#   get_t0, get_postwait_t0             possibly make the above two methods properties for the case where latency is a float, and have them raise an error if it's not, directing the user to use these methods instead.

