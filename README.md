# labscript_core

An experiment in a more careful timing model for labscript.

If successful, it may be included in a future version of labscript as an
underlying layer for timing calculations. Unit conversions, device properties,
globals and interaction with HDF5 files etc can likely remain in the higher,
existing layer, with this layer just being about getting the timing right.

The code is very incomplete, and as functionality is added back in to
reproduce what labscript can currently do timing-wise, it may become apparent
that the structure here is not appropriate, so it may change radically and
should not be taken too seriously.

Written in Python 3.6, but can easily make compatible with both major Python
versions if this is not practical to by the time labscript v3 comes around.