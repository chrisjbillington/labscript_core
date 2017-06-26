import traceback
import weakref

from enforce_phase import phase, enforce_phase, has_phase_enforced_methods
from utils import formatobj


class HasParent(object, metaclass=has_phase_enforced_methods):
    """Base class for all objects that have a parent, such as Instructions and
    Devices. For our purposes the Shot class is also an instance of HasParent
    - its parent is itself. The main purpose of this class presently is to hook
    into the debugging and testing functionality of the @enforce_phase decorator,
    which requires some metaclass magic to work correctly."""

    def __init__(self, parent):
        self.parent = parent
        if parent is self:
            from shot import Shot
            if not isinstance(self, Shot):
                msg = "Only a Shot can be its own parent"
                raise TypeError(msg)
            self.shot = self
        else:
            self.shot = parent.shot

        # Add self to the phase enforcer's registry of all instances:
        enforce_phase.register_instance(self)


class Instruction(HasParent):
    @enforce_phase(phase.ADD_INSTRUCTIONS)
    def __init__(self, parent, t, *args, _inst_depth=1, **kwargs):
        """Base instruction class. Has an initial time, and that's about it.
        _inst_depth is the stack depth of functions that are wrappers around
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
        super().__init__(parent)
        self.t = t
        self.parent.add_instruction(self)
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

    @enforce_phase(phase.CONVERT_TIMING, exactly_once=True)
    def convert_timing(self, waits):
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


class HasChildren(HasParent):
    """Base class for HasInstructions and HasDevices to allow cooperative
    multiple inheritance from them"""
    def descendant_instructions(self, recurse_into_pseudoclocks=False):
        return []


class HasDevices(HasChildren):
    """Mixin for objects that have child devices, currently: Shot and
    Device."""
    # HasDevices.allowed_devices = [] will be replaced with
    # HasDevices.allowed_devices = [Device] after the Device class is defined
    # below in this file (the name Device is not yet available). Subclasses
    # should override this class attribute to specify which devices are
    # allowed as children.
    allowed_devices = []
    def __init__(self, parent):
        super().__init__(parent)
        self.devices = []

        # Used to enforce that the two methods establish_common_limits() and
        # establish_initial_attributes() are called exactly once during
        # compilation:
        self.common_limits_established = False
        self.initial_attributes_established = False

    @enforce_phase(phase.ADD_DEVICES)
    def add_device(self, device):
        if not any(isinstance(device, cls) for cls in self.allowed_devices):
            msg = (f"Device of type {device.__class__.__name__} "
                   f"not permitted as child of {self}.")
            raise TypeError(msg)
        self.devices.append(device)

    def descendant_devices(self, recurse_into_pseudoclocks=False):
        """Recursively return devices that are descendants of this instance
        (not including this instance itself). If recurse_into_pseudoclocks is
        True, then pseudoclocks that are descendants of this instance, and all
        of their descendants (including further pseudoclocks and so on) will
        be returned as well, otherwise they will be excluded."""
        from devices import Pseudoclock
        devices = []
        for device in self.devices:
            if isinstance(device, Pseudoclock) and not recurse_into_pseudoclocks:
                continue
            else:
                devices.append(device)
                devices.extend(device.descendant_devices(recurse_into_pseudoclocks))
        return devices

    def descendant_instructions(self, recurse_into_pseudoclocks=False):
        """Recursively return instructions of all devices that are descendants
        of this instance, including its own instructions (if any). If
        recurse_into_pseudoclocks is True, then instructions of pseudoclocks
        that are descendants of this instance, and all of their descendants
        (including further pseudoclocks and so one) will be returned as well,
        otherwise they will be excluded."""
        from devices import Pseudoclock
        instructions = super().descendant_instructions(recurse_into_pseudoclocks)
        for device in self.devices:
            if isinstance(device, Pseudoclock) and not recurse_into_pseudoclocks:
                continue
            else:
                instructions.extend(device.descendant_instructions(recurse_into_pseudoclocks))
        return instructions

    @enforce_phase(phase.ESTABLISH_COMMON_LIMITS, exactly_once=True)
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

    @enforce_phase(phase.ESTABLISH_INITIAL_ATTRIBUTES, exactly_once=True)
    def establish_initial_attributes(self):
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
        mostly informational, such as t0, ancestor_latency, and other data that the
        user might find it convenient to have when issuing instructions."""
        for device in self.devices:
            device.establish_initial_attributes()

    def __repr__(self):
        return self.__str__()


class HasInstructions(HasChildren):
    """Mixin for objects that have instructions, currently: Shot (which can
    have wait instructions) and Output (which can have all other
    instructions)."""
    allowed_instructions = [Instruction]
    def __init__(self, parent):
        super().__init__(parent)
        self.instructions = []

    @enforce_phase(phase.ADD_INSTRUCTIONS)
    def add_instruction(self, instruction):
        if not any(isinstance(instruction, cls) for cls in self.allowed_instructions):
            msg = f"Instruction of type {device.__class__.__name__} not permitted by {self}"
            raise TypeError(msg)
        self.instructions.append(instruction)

    def descendant_instructions(self, recurse_into_pseudoclocks=False):
        # When a subclass inherits from both HasInstructions and HasDevices,
        # this method ensures the instances own instructions are returned as well
        # as those of child devices
        instructions = super().descendant_instructions(recurse_into_pseudoclocks)
        instructions.extend(self.instructions)
        return instructions

    def __repr__(self):
        return self.__str__()


class Device(HasDevices):
    # Device.allowed_devices = [] will be replaced with Device.allowed_devices
    # = [Device], after class construction is complete (the name is not yet
    # available). Subclasses should override this class attribute to specify
    # which devices are allowed as children:
    allowed_devices = []
    output_delay = 0
    @enforce_phase(phase.ADD_DEVICES)
    def __init__(self, name, parent, connection):
        super().__init__(parent)
        self.name = name
        self.connection = connection
        self.parent.add_device(self)
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


# Now that Device is defined, we can set allowed_devices on HasDevices and
# Device:
HasDevices.allowed_devices = [Device]
Device.allowed_devices = [Device]


class Output(Device, HasInstructions):
    allowed_instructions = [OutputInstruction]
    allowed_devices = [Device]
    def __init__(self, name, parent, connection):
        super().__init__(name, parent, connection)  

    # TODO: put these in non-core so that this Output class can be a base
    # class for static outputs too. Or add a DynamicOutput class that these
    # belong to. Or maybe leave them in and have StaticOutput reimplement them
    # with just raising TypeError.

    def function(self, t, duration, function, samplerate, _inst_depth=1):
        from instructions import Function
        Function(self, t, duration, function, samplerate, _inst_depth=_inst_depth+1)
        return duration

    def constant(self, t, value, _inst_depth=1):
        from instructions import Constant
        Constant(self, t, value, _inst_depth=_inst_depth+1)
        return 0


