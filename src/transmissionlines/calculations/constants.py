"""Numerical limits for transmission-line calculation algorithms."""

# Reject catenary sinh arguments above this bound before hyperbolic overflow.
SAG_MAX_CATENARY_SINH_ARGUMENT = 700

# Limit the number of halving or doubling steps when seeking a positive root bracket.
SAG_MAX_BRACKET_STEPS = 1024

# Limit bisection iterations if the length and tension criteria cannot both be met.
SAG_MAX_BISECTION_STEPS = 256

# Maximum length residual as a fraction of the stressed reference arc length.
SAG_RELATIVE_LENGTH_TOLERANCE = 1e-11

# Maximum tension-bracket width as a fraction of the trial horizontal tension.
SAG_RELATIVE_TENSION_TOLERANCE = 1e-10

# Allow this many feet of roundoff when locating the chord-relative sag maximum.
SAG_POSITION_TOLERANCE_FT = 1e-9

# Allow this many feet of negative roundoff before rejecting calculated sag.
SAG_NEGATIVE_DROP_TOLERANCE_FT = 1e-9

# Bound hypothetical span-grid intervals before allocating the sample list.
SAG_MAX_GRID_POINTS = 1_000_000

# Absolute foot tolerance passed to isclose when comparing the grid endpoint.
SAG_GRID_ENDPOINT_TOLERANCE_FT = 1e-10

# Smallest nominal-pi series impedance accepted for equivalent-pi division, in ohms.
ST_CLAIR_MIN_SERIES_IMPEDANCE_OHM = 1e-15

# Smallest series reactance allowed without an explicit near-zero override, in ohms.
ST_CLAIR_MIN_SERIES_REACTANCE_OHM = 1e-12

# Maximum allowed three-mesh matrix condition number before rejecting a solve.
ST_CLAIR_MAX_MESH_CONDITION_NUMBER = 1e14

# Extend the line-length arange stop by half a step to include exact grid endpoints.
ST_CLAIR_LENGTH_GRID_STOP_PADDING_STEPS = 0.5

# Number of bisection steps for the first voltage or thermal boundary crossing.
ST_CLAIR_BOUNDARY_REFINEMENT_STEPS = 18