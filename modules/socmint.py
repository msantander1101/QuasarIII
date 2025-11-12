import streamlit as st
import asyncio
from typing import List, Dict
from utils.rate_limiter import RateLimiter
import pandas as pd

class SOCMINTOrchestrator:
    def __init__(self, user_id, db_manager, config_manager):
        self.user_id = user_id
        self.db = db_manager
        self.config = config_manager
        self.limiter = RateLimiter(delay=1.5)

        self.sources = {
            "sherlock": {"enabled": True, "priority": 1},
            "maigret": {"enabled": True, "priority": 2},
            "whatsmyname": {"enabled": True, "priority": 3},
        }

    async def search_sherlock(self, username: str) -> List[Dict]:
        """Sherlock con proxy"""
        try:
            import sherlock_project.sherlock as sherlock
            from sherlock_project.sherlock import QueryStatus

            sites = sherlock.sherlock.load_sites()
            high_priority = ["Twitter", "Instagram", "Facebook", "LinkedIn", "GitHub"]
            sites_filtered = {k: v for k, v in sites.items() if k in high_priority or False}

            results = await sherlock.sherlock(
                username=username,
                site_data=sites_filtered,
                timeout=45
            )

            return [
                {
                    "platform": site,
                    "url": data['url_user'],
                    "status": "FOUND" if data['status'].status == QueryStatus.CLAIMED else "NOT_FOUND",
                    "category": self._categorize(site),
                    "source": "sherlock"
                }
                for site, data in results.items()
                if data['status'].status == QueryStatus.CLAIMED
            ]
        except Exception as e:
            st.error(f"Sherlock error: {e}")
            return []

    def _categorize(self, platform: str) -> str:
        categories = {
            "Social": ["twitter", "instagram", "facebook"],
            "Professional": ["linkedin", "github"],
            "Gaming": ["steam", "twitch"],
        }
        for cat, keywords in categories.items():
            if any(k in platform.lower() for k in keywords):
                return cat
        return "Other"

    def render_ui(self):
        st.header("📱 SOCMINT - Multi-Fuente")

        username = st.text_input("Username", placeholder="juanperez")

        if st.button("Buscar en 15+ Fuentes", type="primary"):
            if not username:
                st.error("❌ Ingresa username")
                return

            with st.spinner("Buscando..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(self.search_sherlock(username))

            if results:
                st.success(f"✅ {len(results)} perfiles encontrados")
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)
                st.session_state.results_socmint = {"profiles": results}
            else:
                st.warning("❌ No encontrado")