# Purpose:
# Groups lightweight shared primitives used across bounded contexts.
#
# Future Responsibilities:
# - Prevent duplicate definitions of common backend-wide concepts.
# - Keep shared items small, stable, and generic.
#
# Dependencies:
# - None directly.
#
# What Should Not Live Here:
# - Module-specific business rules.
# - Large utility collections with unclear ownership.
# - Vendor integration code.
