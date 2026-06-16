# Purpose:
# Contains the transport layer exposed to users, agents, and future models.
#
# Future Responsibilities:
# - Keep HTTP-facing concerns separate from business logic.
# - Translate incoming requests into application use-case inputs.
# - Translate application outputs into API responses.
#
# Dependencies:
# - backend.api.router
# - backend.api.dependencies
#
# What Should Not Live Here:
# - Domain decision-making.
# - Database access logic.
# - Direct external market API calls.
