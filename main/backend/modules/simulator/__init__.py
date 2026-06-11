# Purpose:
# Marks the simulator bounded context for environment and portfolio simulation.
#
# Future Responsibilities:
# - Encapsulate all rules related to isolated simulator environments.
# - Keep user, AI, and future RL environments operating under the same internal model.
#
# Dependencies:
# - backend.modules.market_data
#
# What Should Not Live Here:
# - Direct HTTP request handling.
# - External market vendor adapters.
# - Unrelated future modules such as news or research.
