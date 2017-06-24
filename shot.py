from bases import HasDevices, HasInstructions
from instructions import Wait
from devices import PseudoclockDevice, StaticDevice, Pseudoclock
from utils import formatobj, sort_by_time


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
        self.all_devices = None
        self.all_pseudoclocks = None
        self.total_instructions = 0

        # For our child devices looking to inherit shot and pseudoclock from
        # their parent:
        self.shot = self
        self.pseudoclock = None

    def add_device(self, device):
        if isinstance(device, PseudoclockDevice):
            if self.master_pseudoclock is not None:
                raise ValueError(f"Cannot add second master pseudoclock "
                                 f"device '{device.name}'. Already have master "
                                 f"pseudoclock device '{self.master_pseudoclock.name}'")
            self.master_pseudoclock = device
        super().add_device(device)

    def establish_common_limits(self):
        super().establish_common_limits()
        # TODO: determine nominal wait duration

    def start(self):
        # Populate lists of devices:
        self.all_devices = self.descendant_devices(recurse_into_pseudoclocks=True)
        self.all_pseudoclocks = [d for d in self.all_devices if isinstance(d, Pseudoclock)]

        # Have devices compute the limitations common to their children
        self.establish_common_limits()
        # Have devices inherit the information they need from their parents, 
        # including those common limits they are interested in.
        self.update_initial_attributes()

        # TODO: trigger pseudoclocks.
        # TODO: Enum for trigger start time - EARLIEST LATEST
        # TODO: return max delay? Maybe only max delay of pseudoclocks that didn't have
        # an initial trigger time other than minimum set.

    def wait(self, t, name):
        Wait(self, t, name)
        # TODO: triggers

    def compile(self):

        sort_by_time(self.waits)
        
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
        return formatobj(self, 'name')