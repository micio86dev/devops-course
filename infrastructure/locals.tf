# ============================================================================
# locals.tf
# Valori calcolati riusabili (alternativa a variabili che non cambiano mai).
# ============================================================================

locals {
  # Lista di tag applicata a TUTTE le resource che li supportano.
  # Comodo per filtri nel pannello DO o via doctl.
  common_tags = ["devops-course", "tf-managed", "lesson-2"]
}