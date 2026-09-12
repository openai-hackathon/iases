"""Opt-in evaluation limits; dataset metadata cannot supply arbitrary mounts."""


def container_options(profile: str = "") -> dict:
    if not profile:
        # Existing browser evaluations require their legacy sandbox capability.
        return {"cap_add": ["SYS_ADMIN"]}
    if profile == "python_offline":
        return {
            "init": True,
            "network_mode": "none",
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"],
            "mem_limit": "1g",
            "nano_cpus": 1_000_000_000,
            "pids_limit": 128,
        }
    raise ValueError(f"Unknown evaluation container profile: {profile!r}")
