# modules/search/relationship_search.py
import logging
import time
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class RelationshipSearcher:
    """
    Sistema avanzado de búsqueda de relaciones entre personas
    """

    def __init__(self):
        self.related_people_cache = {}  # Cache para personas relacionadas

    def find_connections(self, person_ids: List[int], max_depth: int = 2) -> Dict[str, Any]:
        """
        Encontrar conexiones entre personas
        """
        start_time = time.time()

        try:
            connections = {
                "person_ids": person_ids,
                "depth": max_depth,
                "connections": [],
                "statistics": {
                    "total_people": 0,
                    "total_links": 0,
                    "average_degree": 0.0
                }
            }

            # Simulación de búsqueda de conexiones
            connections["connections"] = self._generate_mock_relationships(person_ids, max_depth)

            # Calcular estadísticas
            connections["statistics"]["total_people"] = len(connections["connections"])
            connections["statistics"]["total_links"] = sum(
                len(conn.get('related_to', [])) for conn in connections["connections"]
            )

            logger.info(f"Búsqueda de conexiones completada en {time.time() - start_time:.2f}s")

            return connections

        except Exception as e:
            logger.error(f"Error en búsqueda de conexiones: {e}")
            return {"error": f"Error: {str(e)}"}

    def discover_relationship_types(self, person_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Descubrir tipos de relaciones posibles
        """
        relationship_types = [
            {"type": "work_colleague", "description": "Colega de trabajo"},
            {"type": "family_member", "description": "Miembro familiar"},
            {"type": "friend", "description": "Amigo"},
            {"type": "business_partner", "description": "Socio comercial"},
            {"type": "education", "description": "Relación académica"},
            {"type": "social_media", "description": "Contacto en redes sociales"},
            {"type": "shared_connections", "description": "Conexión en común"},
            {"type": "location_based", "description": "Relación por ubicación"}
        ]

        # Simulación de análisis
        if person_data.get('email') and '@' in person_data['email']:
            email_domain = person_data['email'].split('@')[1]
            if '.' in email_domain:
                relationship_types.append({"type": "professional_email", "description": "Email corporativo"})

        return relationship_types

    def suggest_relationships(self, person_a: Dict[str, Any], person_b: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sugerir relaciones posibles entre dos personas
        """
        suggestions = {
            "potential_relationships": [],
            "confidence_scores": {},
            "reasoning": []
        }

        # Análisis de similitud de datos
        similarities = self._analyze_similarity(person_a, person_b)
        confidence = self._calculate_confidence(similarities)

        # Sugerencias de relación basadas en datos
        if person_a.get('company') and person_b.get('company') and person_a['company'] == person_b['company']:
            suggestions["potential_relationships"].append("work_colleague")
            suggestions["confidence_scores"]["work_colleague"] = confidence
            suggestions["reasoning"].append("Ambos trabajan en la misma empresa")

        if person_a.get('location') and person_b.get('location') and person_a['location'] == person_b['location']:
            suggestions["potential_relationships"].append("location_based")
            suggestions["confidence_scores"]["location_based"] = confidence
            suggestions["reasoning"].append("Ambos están en la misma ubicación")

        if person_a.get('email') and person_b.get('email'):
            if (person_a['email'].split('@')[1] == person_b['email'].split('@')[1]):
                suggestions["potential_relationships"].append("same_domain")
                suggestions["confidence_scores"]["same_domain"] = confidence * 0.8
                suggestions["reasoning"].append("Tienen el mismo dominio de correo")

        return suggestions

    def _generate_mock_relationships(self, person_ids: List[int], depth: int) -> List[Dict[str, Any]]:
        """Generar datos de relaciones simulados"""
        relationships = []

        for i, person_id in enumerate(person_ids):
            connection = {
                "person_id": person_id,
                "related_to": [],
                "relationship_strength": 0,
                "timestamp": time.time()
            }

            for j in range(0, min(len(person_ids) - 1, 3)):
                if i != j:
                    related_person_id = person_ids[j]
                    related_person = {
                        "id": related_person_id,
                        "name": f"Persona {related_person_id}",
                        "relationship_type": "conocido",
                        "confidence": 0.75
                    }
                    connection["related_to"].append(related_person)

            relationships.append(connection)

        return relationships

    def _analyze_similarity(self, person_a: Dict[str, Any], person_b: Dict[str, Any]) -> Dict[str, float]:
        """Analizar similaridades entre dos personas"""
        similarities = {}

        if person_a.get('name') and person_b.get('name'):
            similarities['name_similarity'] = self._calculate_string_similarity(
                person_a['name'], person_b['name']
            )
        else:
            similarities['name_similarity'] = 0.0

        if person_a.get('email') and person_b.get('email'):
            similarities['email_similarity'] = 1.0 if (
                    person_a['email'] == person_b['email']
            ) else 0.5 if (person_a['email'].split('@')[1] == person_b['email'].split('@')[1]) else 0.0
        else:
            similarities['email_similarity'] = 0.0

        if person_a.get('location') and person_b.get('location'):
            similarities['location_similarity'] = self._calculate_string_similarity(
                person_a['location'], person_b['location']
            )
        else:
            similarities['location_similarity'] = 0.0

        if person_a.get('company') and person_b.get('company'):
            similarities['company_similarity'] = 1.0 if (
                    person_a['company'] == person_b['company']
            ) else 0.5
        else:
            similarities['company_similarity'] = 0.0

        return similarities

    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calcular similitud entre strings"""
        if not str1 or not str2:
            return 0.0

        str1_lower = str1.lower()
        str2_lower = str2.lower()

        if str1_lower == str2_lower:
            return 1.0

        common_chars = set(str1_lower) & set(str2_lower)
        total_chars = set(str1_lower) | set(str2_lower)

        if total_chars:
            return len(common_chars) / len(total_chars)
        else:
            return 0.0

    def _calculate_confidence(self, similarities: Dict[str, float]) -> float:
        """Calcular puntaje de confianza combinado"""
        if not similarities:
            return 0.0

        weights = {
            'name_similarity': 0.3,
            'email_similarity': 0.4,
            'location_similarity': 0.2,
            'company_similarity': 0.1
        }

        total_weighted = sum(
            similarities.get(key, 0) * weight
            for key, weight in weights.items()
        )

        return min(total_weighted, 1.0)


# Instancia global
relationship_searcher = RelationshipSearcher()


# Funciones públicas
def find_connections(person_ids: List[int], max_depth: int = 2) -> Dict[str, Any]:
    """Función pública para encontrar conexiones"""
    return relationship_searcher.find_connections(person_ids, max_depth)


def discover_relationship_types(person_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Descubrir tipos de relación"""
    return relationship_searcher.discover_relationship_types(person_data)


def suggest_relationships(person_a: Dict[str, Any], person_b: Dict[str, Any]) -> Dict[str, Any]:
    """Sugerir relaciones entre personas"""
    return relationship_searcher.suggest_relationships(person_a, person_b)