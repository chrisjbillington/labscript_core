from bases import HasDevices, HasInstructions, phase
from instructions import Wait
from devices import PseudoclockDevice, StaticDevice, Pseudoclock
from utils import formatobj, sort_by_time


__all__ = ['Shot']


class Shot(HasDevices, HasInstructions):
    """Top level object for the compilation"""
    allowed_instructions = [Wait]
    allowed_devices = [PseudoclockDevice, StaticDevice]

    def __init__(self, name, epsilon, *args, **kwargs):
        super().__init__(self)
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

        # The phase of compilation we are up to:
        self.set_phase(phase.ADD_DEVICES)

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
        # TODO: determine nominal_wait_delay from pseudoclocks.

    def start(self):
        # Populate lists of devices:
        self.all_devices = self.descendant_devices(recurse_into_pseudoclocks=True)
        self.all_pseudoclocks = [d for d in self.all_devices if isinstance(d, Pseudoclock)]

        # Have devices compute the limitations common to their children
        self.set_phase(phase.ESTABLISH_COMMON_LIMITS)
        self.establish_common_limits()

        # Have devices inherit the information they need from their parents, 
        # including those common limits they are interested in.
        self.set_phase(phase.ESTABLISH_INITIAL_ATTRIBUTES)
        self.establish_initial_attributes()

        self.set_phase(phase.ADD_INSTRUCTIONS)
        # TODO: trigger pseudoclocks.
        # TODO: Enum/dummy for trigger start time? - EARLIEST LATEST etc? arithmetic? - t0, t0 + etc. 
        # TODO: return max delay? Maybe only max delay of pseudoclocks that didn't have
        # an initial trigger time other than minimum set.

    def wait(self, t, name, _inst_depth=1):
        Wait(self, t, name, _inst_depth=_inst_depth+1)
        # TODO: triggers

    def stop(self, t):

        # TODO: add stop instruction?

        # Question, when do we quantise the wait instructions?
        # When do we sort them? Do other instructions need this during their
        # convert_timing() calls?
        sort_by_time(self.waits)

        self.set_phase(phase.CONVERT_TIMING)
        # TODO tell all instructions to convert their timing

        self.set_phase(CHECK_INSTRUCTIONS_VALID)
        # Todo call the recursive methods that check validity of instructions at each level

        
        
        # TODO: Tell all instructions to quantise and relativise their times 
        # TODO Error check upward. First on all instructions, then on parent devices upward one
        # layer at a time. Each layer should do the error checks that are most appropriate for that
        # level.
        


    def __str__(self):
        return formatobj(self, 'name')
