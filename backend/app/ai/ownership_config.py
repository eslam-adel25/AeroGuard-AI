"""Configuration for bag ownership association behavior in the AI overlay pipeline."""

# Minimum number of consecutive frames that must match before a bag is assigned.
OWNERSHIP_ASSIGNMENT_REQUIRED_FRAMES = 3

# Minimum number of consecutive frames without a matching owner before ownership is lost.
OWNERSHIP_LOSS_REQUIRED_FRAMES = 3

# Maximum spatial distance in pixels between a bag and a person for an ownership candidate.
OWNERSHIP_MAX_DISTANCE_PX = 220

# Time a bag may remain unattended before the system escalates to the unattended state.
UNATTENDED_TIMEOUT_SECONDS = 60
