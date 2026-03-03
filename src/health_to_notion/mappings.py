"""All mapping constants for Strava sport types, icons, modalities, and intensity."""

# ---------------------------------------------------------------------------
# Activity Emojis: Strava sport_type -> Notion emoji icon
# ---------------------------------------------------------------------------
ACTIVITY_EMOJIS: dict[str, str] = {
    # Running
    "Run": "\U0001f3c3",
    "TrailRun": "\U0001f3d4\ufe0f",
    "VirtualRun": "\U0001f3c3",
    # Cycling
    "Ride": "\U0001f6b4",
    "MountainBikeRide": "\U0001f6b5",
    "GravelRide": "\U0001f6b4",
    "EBikeRide": "\U0001f6b4",
    "EMountainBikeRide": "\U0001f6b5",
    "VirtualRide": "\U0001f6b4",
    "Velomobile": "\U0001f6b4",
    # Swimming
    "Swim": "\U0001f3ca",
    # Walking
    "Walk": "\U0001f6b6",
    "Hike": "\U0001f97e",
    # Strength & Fitness
    "WeightTraining": "\U0001f3cb\ufe0f",
    "Crossfit": "\U0001f525",
    "HighIntensityIntervalTraining": "\U0001f525",
    "Elliptical": "\U0001f3c3",
    "StairStepper": "\U0001f6b6",
    "Workout": "\U0001f4aa",
    # Yoga & Pilates
    "Yoga": "\U0001f9d8",
    "Pilates": "\U0001f9d8",
    # Rowing
    "Rowing": "\U0001f6a3",
    "VirtualRow": "\U0001f6a3",
    # Racquet Sports
    "Tennis": "\U0001f3be",
    "Racquetball": "\U0001f3be",
    "Badminton": "\U0001f3f8",
    "Pickleball": "\U0001f3d3",
    "Squash": "\U0001f3be",
    "TableTennis": "\U0001f3d3",
    # Team Sports
    "Soccer": "\u26bd",
    # Winter Sports
    "AlpineSki": "\u26f7\ufe0f",
    "BackcountrySki": "\u26f7\ufe0f",
    "NordicSki": "\u26f7\ufe0f",
    "Snowboard": "\U0001f3c2",
    "Snowshoe": "\U0001f97e",
    "IceSkate": "\u26f8\ufe0f",
    # Water Sports
    "Kayaking": "\U0001f6f6",
    "Canoeing": "\U0001f6f6",
    "StandUpPaddling": "\U0001f3c4",
    "Surfing": "\U0001f3c4",
    "Kitesurf": "\U0001f3c4",
    "Windsurf": "\U0001f3c4",
    "Sail": "\u26f5",
    # Climbing
    "RockClimbing": "\U0001f9d7",
    # Other
    "Golf": "\u26f3",
    "Skateboard": "\U0001f6f9",
    "InlineSkate": "\u26f8\ufe0f",
    "Handcycle": "\U0001f6b4",
    "Wheelchair": "\U0001f9bd",
    "RollerSki": "\u26f7\ufe0f",
}

DEFAULT_EMOJI = "\U0001f3c5"

# ---------------------------------------------------------------------------
# Strava sport_type -> Notion "Type" (broad category)
# ---------------------------------------------------------------------------
TYPE_MAP: dict[str, str] = {
    "Run": "Running",
    "TrailRun": "Running",
    "VirtualRun": "Running",
    "Ride": "Cycling",
    "MountainBikeRide": "Cycling",
    "GravelRide": "Cycling",
    "EBikeRide": "Cycling",
    "EMountainBikeRide": "Cycling",
    "VirtualRide": "Cycling",
    "Velomobile": "Cycling",
    "Swim": "Swimming",
    "Walk": "Walking",
    "Hike": "Walking",
    "WeightTraining": "Strength",
    "Crossfit": "Crossfit",
    "HighIntensityIntervalTraining": "HIIT",
    "Elliptical": "Cardio",
    "StairStepper": "Cardio",
    "Workout": "Other",
    "Yoga": "Yoga/Pilates",
    "Pilates": "Yoga/Pilates",
    "Rowing": "Rowing",
    "VirtualRow": "Rowing",
    "Tennis": "Racquet Sports",
    "Racquetball": "Racquet Sports",
    "Badminton": "Racquet Sports",
    "Pickleball": "Racquet Sports",
    "Squash": "Racquet Sports",
    "TableTennis": "Racquet Sports",
    "Soccer": "Team Sports",
    "AlpineSki": "Winter Sports",
    "BackcountrySki": "Winter Sports",
    "NordicSki": "Winter Sports",
    "Snowboard": "Winter Sports",
    "Snowshoe": "Winter Sports",
    "IceSkate": "Winter Sports",
    "Kayaking": "Water Sports",
    "Canoeing": "Water Sports",
    "StandUpPaddling": "Water Sports",
    "Surfing": "Water Sports",
    "Kitesurf": "Water Sports",
    "Windsurf": "Water Sports",
    "Sail": "Water Sports",
    "RockClimbing": "Climbing",
    "Golf": "Golf",
    "Skateboard": "Other",
    "InlineSkate": "Other",
    "Handcycle": "Cycling",
    "Wheelchair": "Other",
    "RollerSki": "Winter Sports",
}

# ---------------------------------------------------------------------------
# Strava sport_type -> Workout Modality (more specific grouping)
# ---------------------------------------------------------------------------
MODALITY_MAP: dict[str, str] = {
    "Run": "Running",
    "TrailRun": "Running",
    "VirtualRun": "Running",
    "Ride": "Outdoor Cycling",
    "MountainBikeRide": "Outdoor Cycling",
    "GravelRide": "Outdoor Cycling",
    "EBikeRide": "Outdoor Cycling",
    "EMountainBikeRide": "Outdoor Cycling",
    "VirtualRide": "Indoor Cycling",
    "Velomobile": "Outdoor Cycling",
    "Swim": "Swimming",
    "Walk": "Walking",
    "Hike": "Walking",
    "WeightTraining": "Strength Training",
    "Crossfit": "Crossfit",
    "HighIntensityIntervalTraining": "HIIT",
    "Elliptical": "Cardio",
    "StairStepper": "Cardio",
    "Workout": "Other",
    "Yoga": "Yoga",
    "Pilates": "Pilates",
    "Rowing": "Rowing",
    "VirtualRow": "Rowing",
    "Tennis": "Racquet Sports",
    "Racquetball": "Racquet Sports",
    "Badminton": "Racquet Sports",
    "Pickleball": "Racquet Sports",
    "Squash": "Racquet Sports",
    "TableTennis": "Racquet Sports",
    "Soccer": "Team Sports",
    "AlpineSki": "Winter Sports",
    "BackcountrySki": "Winter Sports",
    "NordicSki": "Winter Sports",
    "Snowboard": "Winter Sports",
    "Snowshoe": "Winter Sports",
    "IceSkate": "Winter Sports",
    "Kayaking": "Water Sports",
    "Canoeing": "Water Sports",
    "StandUpPaddling": "Water Sports",
    "Surfing": "Water Sports",
    "Kitesurf": "Water Sports",
    "Windsurf": "Water Sports",
    "Sail": "Water Sports",
    "RockClimbing": "Climbing",
    "Golf": "Golf",
    "Skateboard": "Other",
    "InlineSkate": "Other",
    "Handcycle": "Outdoor Cycling",
    "Wheelchair": "Other",
    "RollerSki": "Winter Sports",
}

# ---------------------------------------------------------------------------
# Activity name overrides (for combat sports etc. tagged as "Workout" in Strava)
# ---------------------------------------------------------------------------
NAME_OVERRIDE_MAP: dict[str, str] = {
    "BJJ": "BJJ",
    "Jiu Jitsu": "BJJ",
    "Boxing": "Combat Sports",
    "Kickboxing": "Combat Sports",
    "MMA": "Combat Sports",
    "Sauna": "Sauna",
}

# ---------------------------------------------------------------------------
# Suffer Score -> Intensity (Strava Relative Effort)
# ---------------------------------------------------------------------------
SUFFER_SCORE_THRESHOLDS: list[tuple[int, str]] = [
    (50, "Easy"),
    (150, "Moderate"),
    (300, "Hard"),
]
SUFFER_SCORE_MAX_INTENSITY = "Maximum"

# ---------------------------------------------------------------------------
# Modalities where Easy intensity doesn't apply -> minimum
# ---------------------------------------------------------------------------
INTENSITY_FLOOR: dict[str, str] = {
    "HIIT": "Moderate",
    "BJJ": "Moderate",
    "Crossfit": "Moderate",
    "Combat Sports": "Moderate",
}

# ---------------------------------------------------------------------------
# Skip these activity types (not real workouts)
# ---------------------------------------------------------------------------
SKIP_TYPES: set[str] = set()
