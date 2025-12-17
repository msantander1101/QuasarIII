def search_social_by_usernames(usernames: set) -> dict:
    results = {}
    for u in usernames:
        res = search_social_profiles(u)
        if res and res.get("social_profiles"):
            results[u] = res["social_profiles"]
    return results
