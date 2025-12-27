
---

# 📌 `ROADMAP.md` (para pegar)

```markdown
# 🛣 ROADMAP — QuasarIII

Este roadmap representa las próximas fases planificadas sin romper la arquitectura actual.

---

## 🚩 FASE 1 — Hardening (ACTUAL)
✔ Autenticación obligatoria  
✔ Eliminación de registro público  
✔ Panel administrador (alta/baja/roles)  
✔ Unificación inicial de outputs OSINT  
✔ Logs básicos + trazabilidad (`trace_id`)  

Deliverables:
- [x] README profesional
- [x] AuthManager + create_admin_user
- [x] Admin Users Page
- [x] Breach pipeline defensivo básico

---

## 🚩 FASE 2 — Permisos & Control Operacional
⏳ Próximo

- Control por rol: `analyst`, `senior`, `admin`
- Lógica de permisos por módulo (dorks, darkweb, breach)
- Logging estructurado (ELK, Graylog, Wazuh-ready)
- Rate-limit de fuentes sensibles

Deliverables:
- [ ] PermissionManager
- [ ] Matriz de capacidades por rol
- [ ] Auditoría mínima por acción

---

## 🚩 FASE 3 — API Externa & Integración con OpenCTI
📅 Planificada

- Exponer `/api/search` para enriquecimiento remoto
- Conector OSINT (OpenCTI → QuasarIII)
- Push de hallazgos a STIX2 (QuasarIII → OpenCTI)
- Normalización: Identity, ObservedData, Indicator, Relationship

Deliverables:
- [ ] API Doc
- [ ] Conector PyCTI
- [ ] STIX mapping templates

---

## 🚩 FASE 4 — Inteligencia Avanzada
🔮 Visión

- Scoring de exposición por entidad
- Data Lake OSINT
- Modelos de correlación (NLP + embeddings)
- Playbooks automáticos estilo SOAR light

---

## ✔ Estado
| Fase | Estado |
|------|--------|
| Fase 1 | 🟢 Completada |
| Fase 2 | 🟡 Siguiente |
| Fase 3 | 🔵 En diseño |
| Fase 4 | 🟣 Largo plazo |

