def derive_usernames_from_email(email: str) -> set:
    local = email.split("@")[0]
    base = local.replace(".", "").replace("_", "")
    return {
        local,
        base,
        local.lower(),
        base.lower()
    }
