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



# Pseudoclock.establish_nominal_limits()
#   Get all the deets from children
#   compute all the things you can
#   Tell the kiddos to inherit the things they need
#   Tell the shot about your wait duration
#   Receive from shot about the nominal wait delay
#   Tell children to calculate their prewait overtime based on this

# Variable names:
#   latency:                float or dict by connection, or dict by instruction class. Or override get_latency(dev or inst)
#   cum_latency:            float. latency including all channels up to the master pseudoclock
#   min_trigger_duration:   float. minimum trigger required by TriggerableDevice or ClockableDevice
#   common_min_trigger_duration:   float: min trigger duration that satisfies all devices under this pseudoclock (rounded up to timebase)
#   wait_delay:             float: how long a pseudoclock waits at minimum
#   nom_wait_delay:         float: property of shot: the wait delay that satisfies all devices
#   prewait_overtime        float: how long a device can still issue instructions after a wait() before the wait occurs for it.
#   clock_limit:            int: shortest clock tick a PseudoClock can make or a ClockedDevice can receive (mult. of timebase)
#   common_clock_limit:     int: shortest clock tick all devices under this pseudoclock can deal with (mult. of timebase)
#   t0:                     float: initial trigger time of parent pseudoclock + summed latency from it down
#   postwait_t0:            float: alias for cum_latency

