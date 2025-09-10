class MultilingualService:
    def __init__(self):
        self.templates = {
            "en": {
                "hash_match": "🚨 ALERT: Hash {hash} detected on {system} - Case #{case_id}",
                "critical_match": "🔴 CRITICAL: High-risk hash {hash} found - Immediate action required"
            },
            "es": {
                "hash_match": "🚨 ALERTA: Hash {hash} detectado en {system} - Caso #{case_id}",
                "critical_match": "🔴 CRÍTICO: Hash de alto riesgo {hash} encontrado - Acción inmediata requerida"
            }
        }
