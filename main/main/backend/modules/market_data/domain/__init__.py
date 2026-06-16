# Purpose:
# Contains market data business concepts that remain independent of provider details.
#
# Future Responsibilities:
# - Define the language of instruments, quotes, price history, and metadata.
# - Isolate market data meaning from transport or persistence choices.
#
# Dependencies:
# - backend.shared.types
#
# What Should Not Live Here:
# - Vendor SDK clients.
# - API route code.
# - Cache implementation details.
