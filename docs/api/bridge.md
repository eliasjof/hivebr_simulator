# Bridge & Backends

The bridge adapts the OpenLab API to a concrete execution backend. It is the
only place that knows about `hivebr.engine` (or, in the future, ROS 2), keeping
the public API backend-agnostic.

::: hivebr.bridge
