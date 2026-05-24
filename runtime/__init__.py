"""Sopify runtime package."""

# Kernel-only re-exports.  Heavy legacy imports (engine, models,
# output, preferences) removed during runtime-slimming S4.
# Consumers that previously used ``from runtime import RuntimeConfig``
# should import from ``sopify_contracts`` directly.
