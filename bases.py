import traceback
from utils import formatobj


class Instruction(object):
    def __init__(self, parent, t, *args, _inst_depth=1, **kwargs):
        """Base instruction class. Has an initial time, and that's about it.
        __inst_depth is the stack depth of functions that are wrappers around
        instantiating Instructions. All such functions (including the __init__
        method of subclasses of Instruction) should accept an _inst_depth=1
        keyword argument, and should pass inst_depth=_inst_depth+1 to the
        function they are wrapping (or the __init__ method of the Instruction
        class they are subclassing), in order for the traceback-making code to
        figure out where in the stack user code ends and labscript code
        begins. This is so that we can raise tracebacks that end at the line
        of user code that resulted in creating the instruction (internal
        labscript tracebacks, unless labscript itself has crashed, are not
        useful)."""
        super().__init__(*args, **kwargs)
        self.parent = parent
        self.t = t
        self.parent.add_instruction(self)
        self.shot = parent.shot
        self.pseudoclock = parent.pseudoclock

        # Timing details to be computed during processing:
        self.relative_t = None
        self.quantised_t = None

        # For giving the user a traceback if an error regarding this
        # instruction is found during later processing:
        self.traceback = ''.join(traceback.format_stack()[:-_inst_depth])

        # Count how many instructions there are and save which number we are:
        self.instruction_number = self.parent.shot.total_instructions
        self.parent.shot.total_instructions += 1

    def _convert_times(self, waits):
        """Convert all times specified by this instruction to ones relative to
        the start of our controlling pseudoclock, taking into account the
        effects of waits, and compute them as an integer in units of the
        pseudoclock's timebase. This method converts self.t, producing
        self.relative_t and self.quantised_t. Subclasses implementing this
        method should call our implementation, then convert any additional
        times that they specify to their relative and quantised versions."""
        pass

    def __str__(self):
        return formatobj(self, 'parent', 't')

    def __repr__(self):
        return self.__str__()


class OutputInstruction(Instruction):
    """A class to distinguish non-wait instructions from wait instructions"""
    pass


class HasInstructions(object):
    """Mixin for objects that have instructions, currently: Shot (which can
    have wait instructions) and Output (which can have all other
    instructions)."""
    allowed_instructions = [Instruction]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instructions = []

    def add_instruction(self, instruction):
        if not any(isinstance(instruction, cls) for cls in self.allowed_instructions):
            raise TypeError(f"Instruction of type {device.__class__.__name__} not permitted " 
                            f"by {self}.")
        self.instructions.append(instruction)

    def __repr__(self):
        return self.__str__()


class HasDevices(object):
    """Mixin for objects that have child devices, currently: Shot and
    Device."""
    # Will be interpreted as allowed_devices = [Device], but the name Device
    # is not available yet. Subclasses should override this class attribute to
    # specify which devices are allowed as children:
    allowed_devices = None
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.allowed_devices is None:
            self.allowed_devices = [Device]
        self.devices = []

    def add_device(self, device):
        if not any(isinstance(device, cls) for cls in self.allowed_devices):
            raise TypeError(f"Device of type {device.__class__.__name__} not permitted " 
                            f"as child of {self}.")
        self.devices.append(device)

    def descendant_devices(self, recurse_into_pseudoclocks=False):
        """Recursively return devices that are descendants of this instance
        (not including this instance itself). If recurse_into_pseudoclocks is
        True, then pseudoclocks that are descendants of this instance, and all
        of their descendants (including further pseudoclocks and so on) will
        be returned as well, otherwise they will be excluded."""
        devices = []
        for device in self.devices:
            if isinstance(device, Pseudoclock) or not recurse_into_pseudoclocks:
                continue
            else:
                devices.append(device)
                devices.extend(device.descendant_devices(recurse_into_pseudoclocks))

    def descendant_instructions(self, recurse_into_pseudoclocks=False):
        """Recursively return instructions of all devices that are descendants
        of this instance, including its own instructions (if any). If
        recurse_into_pseudoclocks is True, then instructions of pseudoclocks
        that are descendants of this instance, and all of their descendants
        (including further pseudoclocks and so one) will be returned as well,
        otherwise they will be excluded."""
        if isinstance(self, HasInstructions):
            instructions = self.instructions.copy()
        else:
            instructions = []
        for device in self.devices:
            if isinstance(device, Pseudoclock) or not recurse_into_pseudoclocks:
                continue
            else:
                instructions.extend(device.descendant_instructions(recurse_into_pseudoclocks))

    def establish_common_limits(self):
        """Called during shot.start(), after the device hierarchy has been
        established, but before any instructions have been given. Subclasses
        should implement this method to examine their children and determine
        the minimal limitations that will satisfy all their children's
        individual limitations, such as the smallest clock interval compatible
        with each device's minimum update interval, etc. They should save this
        information in instance attributes or however is appropriate for later
        use and for inspection by their children in the case that they require
        this information. Implementations must call this base implementation
        before establishing their own limits, such that any child device's
        limitations that may depend on *its* children has already been
        established."""
        for device in self.devices:
            device.establish_common_limits()

    #TODO: rename? configure initial attributes? get? set? assign?
    def update_initial_attributes(self):
        """called during shot.start(), after the device hierarchy has been
        established, and after common limits have been established, but before
        any instructions have been given. Subclasses should implement this
        method to access the common limits they are interested in from their
        parent devices, as determined in HasDevice.establish_common_limits(),
        as well as any other information such as initial trigger times, and
        update their attributes accordingly. This information must not
        invalidate the results of any parent device's
        establish_common_limits(), which has already been called and will not
        be called again. Information set on child devices with this method is
        mostly informational, such as t0, cum_latency, and other data that the
        user might find it convenient to have when issuing instructions."""
        for device in self.devices:
            device.update_initial_attributes()

    def __repr__(self):
        return self.__str__()


class Device(HasDevices):
    # allowed_devices = None will be interpreted as allowed_devices =
    # [Device], but the name Device is not available during class
    # construction. Subclasses should override this class attribute to specify
    # which devices are allowed as children:
    allowed_devices = None
    output_delay = 0

    def __init__(self, name, parent, connection, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.parent = parent
        self.connection = connection
        self.parent.add_device(self)
        self.shot = self.parent.shot
        self.pseudoclock = self.parent.pseudoclock

    def get_output_delay(self, child):
        """The time elapsed between receiving a trigger/clock tick and
        providing output to a given child device or Instruction. Should be
        zero for top level devices. Subclasses should either set a class or
        instance attribute if delays are constant, or should reimplement this
        function if delays depend on the child device or instruction"""
        return self.output_delay

    def __str__(self):
        return formatobj(self, 'name', 'parent', 'connection')


class Output(Device, HasInstructions):
    allowed_instructions = [OutputInstruction]
    allowed_devices = [Device]
    def __init__(self, name, parent, connection, *args, **kwargs):
        super().__init__(name, parent, connection, *args, **kwargs)  

    # TODO: put these in non-core so that this Output class
    # can be a base class for static outputs too

    def function(self, t, duration, function, samplerate, _inst_depth=1):
        from instructions import Function
        Function(self, t, duration, function, samplerate, _inst_depth=_inst_depth+1)
        return duration

    def constant(self, t, value, _inst_depth=1):
        from instructions import Constant
        Constant(self, t, value, _inst_depth=_inst_depth+1)
        return 0


