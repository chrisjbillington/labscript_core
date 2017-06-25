import numpy as np

from bases import Instruction, Device, Output

from instructions import Wait, OutputInstruction, Function, Constant, Static

from devices import (StaticDevice, StaticOutput, TriggerableDevice, Trigger, ClockableDevice,
                     ClockLine, Pseudoclock, PseudoclockDevice)

from shot import Shot


if __name__ == '__main__':
    shot = Shot('<shot>', 100e-9)
    pulseblaster = PseudoclockDevice('pulseblaster', shot, None, minimum_trigger_duration=0.1)
    pulseblaster_clock = Pseudoclock('pulseblaster_clock', pulseblaster, 'clock',
                                     clock_limit=1, wait_delay=0.5, timebase=0.1)
    clockline = ClockLine('clockline', pulseblaster_clock, 'flag 1')
    ni_card = ClockableDevice('ni_card', clockline, 'clock', minimum_trigger_duration=0.1, clock_limit=1.2)
    ao = Output('ao', ni_card, 'ao0')
    shot.start()
    shot.wait(t=7, name='first_wait')
    ao.constant(t=0, value=7)
    ao.function(t=0, duration=7, function=np.sin, samplerate=20)


# TODO list:
# Implement pseudoclock.establish_common_limitations:
#   Pseudoclocks need to:
#       Check clock_limit of all of their child ClockedDevices
#       Check trigger_minimum_duration of all of their ClockedDevices and TriggerableDevices?
#           On a per-clockline basis, or is this too complicated? 

# Timing variable names:
#   latency:                            float or dict-->float by connection, or dict-->float by instruction class, giving this device's contribution to latency to that child
#   get_latency:                        method returning the above for a given child device or instruction, or with no args if latency is a float
#   ancestor_latency:                   float. latency including all parents up to the master pseudoclock (not including own latency)
#   trigger_minimum_duration:           float. minimum trigger required by TriggerableDevice or ClockableDevice
#   common_trigger_minimum_duration:    float: min trigger duration that satisfies all devices under this pseudoclock (rounded up to timebase)
#   wait_delay:                         float: how long a pseudoclock waits at minimum
#   nominal_wait_delay:                 float: property of shot: the wait delay that satisfies all devices
#   prewait_overtime                    float: how long a device can still issue instructions after a call to wait() before the wait occurs for it.
#   clock_limit:                        int: shortest clock tick a PseudoClock can make or a ClockedDevice can receive (mult. of timebase)
#   common_clock_limit:                 int: shortest clock tick all devices under this pseudoclock can deal with (mult. of timebase)
#   t0:                                 method returning float: initial trigger time + ancestor_latency + get_latency(device_or_instruction)
#   postwait_t0:                        method returning float: ancestor_latency + get_latency(device_or_instruction)
#   get_t0, get_postwait_t0             possibly make the above two methods properties for the case where latency is a float, and have them raise an error if it's not, directing the user to use these methods instead.

