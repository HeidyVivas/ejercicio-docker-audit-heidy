# Auditoría de Seguridad — ejercicio-docker-audit

**Proyecto:** API Legacy TechNova
**Fase:** 1 — Auditoría
**Herramientas usadas:** Bandit

## Comando de escaneo

```bash
bandit app.py test_app.py -f txt -o auditoria_bandit.txt
```

> Nota: apuntar directo a los archivos del proyecto (o excluir el entorno virtual con `-x ./.venv`) es obligatorio; de lo contrario Bandit escanea también las librerías instaladas y reporta cientos de falsos positivos ajenos al proyecto.

**Resultado real del escaneo:** 34 líneas de código analizadas, 6 hallazgos (1 alto, 2 medios, 3 bajos).

## Tabla de hallazgos

| # | ID Bandit | Archivo / línea | Hallazgo | Severidad | Confianza | Recomendación |
|---|---|---|---|---|---|---|
| 1 | B201 — flask_debug_true | `app.py:35` | `debug=True` expone el debugger de Werkzeug y permite ejecución remota de código | **Alta** | Media | Usar `debug=False` en producción; controlar por variable de entorno |
| 2 | B608 — hardcoded_sql_expressions | `app.py:25` | SQL Injection por concatenación de string en la query de `/buscar` | Media | Baja | Usar consultas parametrizadas (`cursor.execute("... WHERE id = %s", (usuario_id,))`) |
| 3 | B104 — hardcoded_bind_all_interfaces | `app.py:35` | Binding a todas las interfaces (`0.0.0.0`) | Media | Media | Restringir el host o justificar el uso si es necesario en contenedor |
| 4 | B105 — hardcoded_password_string | `app.py:10` | Contraseña de base de datos hardcodeada en texto plano | Baja | Media | Mover a variables de entorno (`.env`, excluido de git vía `.gitignore`) |
| 5 | B311 — blacklist (random) | `app.py:30` | Uso de `random` no apto para fines de seguridad/criptografía | Baja | Alta | No aplica corrección aquí (es simulación de fallo, no uso criptográfico); documentar como aceptado si se mantiene |
| 6 | B101 — assert_used | `test_app.py:7` | Uso de `assert` en pruebas | Baja | Alta | Aceptable en contexto de tests (pytest/unittest); no aplica a código de producción |

## Resumen

- **Hallazgos altos:** 1
- **Hallazgos medios:** 2
- **Hallazgos bajos:** 3

## Siguiente paso

Estos hallazgos se corrigen en la **Fase 2 — Arquitectura**, junto con la creación del `docker-compose.yml` y el refactor del código con buenas prácticas.