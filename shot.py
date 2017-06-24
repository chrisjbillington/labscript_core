from bases import HasDevices, HasInstructions
from instructions import Wait
from devices import PseudoclockDevice, StaticDevice
from utils import _formatobj, _sort_by_time


__all__ = ['Shot']


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