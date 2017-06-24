import numpy as np
import inspect
import traceback

from bases import Output

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