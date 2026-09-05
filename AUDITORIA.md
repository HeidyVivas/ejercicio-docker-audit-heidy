# Auditoría de Seguridad y Despliegue — ejercicio-docker-audit

**Proyecto:** API Legacy TechNova
**Repositorio:** [github.com/HeidyVivas/ejercicio-docker-audit-heidy](https://github.com/HeidyVivas/ejercicio-docker-audit-heidy)
**Repositorio original (fork de):** [github.com/BlackT1221/ejercicio-docker-audit](https://github.com/BlackT1221/ejercicio-docker-audit)
**Herramientas usadas:** Bandit, Pytest, Trivy, GitHub Actions, Docker, Nginx Proxy Manager, Dozzle, Uptime Kuma

## URLs del proyecto

| Recurso | URL |
|---|---|
| Repositorio (GitHub) | https://github.com/HeidyVivas/ejercicio-docker-audit-heidy |
| Pipeline CI/CD (GitHub Actions) | https://github.com/HeidyVivas/ejercicio-docker-audit-heidy/actions |
| API TechNova (app en producción) | http://heidyaudit1.duckdns.org |
| Dozzle (logs en tiempo real) | http://heidyaudit1-dozzle.duckdns.org |
| Uptime Kuma (monitoreo) | http://heidyaudit1-kuma.duckdns.org |
| Panel de administración Nginx Proxy Manager | http://3.16.119.118:81 |

---

## Fase 1 — Auditoría

Fork del repositorio original y ejecución de pruebas de Bandit en local.

**Comando usado:**
```bash
bandit app.py test_app.py -f txt -o auditoria_bandit.txt
```

> Nota: apuntar directo a los archivos del proyecto (o excluir el entorno virtual con `-x ./.venv`) es obligatorio; de lo contrario Bandit escanea también las librerías instaladas y reporta cientos de falsos positivos ajenos al proyecto.

**Resultado del primer escaneo:** 34 líneas de código analizadas, 6 hallazgos (1 alto, 2 medios, 3 bajos).

### Tabla de hallazgos

| # | ID Bandit | Archivo / línea | Hallazgo | Severidad | Confianza | Recomendación |
|---|---|---|---|---|---|---|
| 1 | B201 — flask_debug_true | `app.py:35` | `debug=True` expone el debugger de Werkzeug y permite ejecución remota de código | **Alta** | Media | Usar `debug=False` en producción; controlar por variable de entorno |
| 2 | B608 — hardcoded_sql_expressions | `app.py:25` | SQL Injection por concatenación de string en la query de `/buscar` | Media | Baja | Usar consultas parametrizadas (`cursor.execute("... WHERE id = %s", (usuario_id,))`) |
| 3 | B104 — hardcoded_bind_all_interfaces | `app.py:35` | Binding a todas las interfaces (`0.0.0.0`) | Media | Media | Restringir el host o justificar el uso si es necesario en contenedor |
| 4 | B105 — hardcoded_password_string | `app.py:10` | Contraseña de base de datos hardcodeada en texto plano | Baja | Media | Mover a variables de entorno (`.env`, excluido de git vía `.gitignore`) |
| 5 | B311 — blacklist (random) | `app.py:30` | Uso de `random` no apto para fines de seguridad/criptografía | Baja | Alta | No aplica corrección aquí (es simulación de fallo, no uso criptográfico); documentar como aceptado si se mantiene |
| 6 | B101 — assert_used | `test_app.py:7` | Uso de `assert` en pruebas | Baja | Alta | Aceptable en contexto de tests (pytest/unittest); no aplica a código de producción |

### Resumen inicial
- **Hallazgos altos:** 1
- **Hallazgos medios:** 2
- **Hallazgos bajos:** 3

---

## Fase 2 — Arquitectura

Refactorización del código aplicando buenas prácticas de seguridad, y contenedorización con Docker.

### Cambios aplicados
- Credenciales movidas a variables de entorno (`.env`, excluido de git) — corrige B105
- Consulta parametrizada en `/buscar` en vez de concatenación de strings — corrige B608
- `debug` controlado por variable de entorno (`DEBUG`), `False` en producción — corrige B201
- Manejo de excepciones (`try/except`) en todas las rutas que tocan la base de datos
- Conexión centralizada a la BD en una función reutilizable (`get_connection`)
- `# nosec` documentado y justificado en los 3 hallazgos aceptados (B104, B311, B101), en vez de ignorarlos silenciosamente

### Segundo escaneo (post-refactor)
```bash
bandit app.py test_app.py -f txt -o auditoria_bandit_v2.txt
```
**Resultado:** `Total issues: 0` en las tres severidades (Low, Medium, High). Los 3 hallazgos con `# nosec` quedan registrados como "Total potential issues skipped" (justificados, no ocultos).

### Infraestructura
- `Dockerfile`: imagen `python:3.12-slim`, instala dependencias desde `requirements.txt`, expone el puerto 5050
- `docker-compose.yml`: servicio `app` (Flask) + servicio `db` (MySQL 8.0) con volumen persistente, variables de entorno vía `env_file: .env`
- Verificado localmente con `docker compose up --build` — endpoints `/`, `/buscar`, `/health` responden correctamente

---

## Fase 3 — Pipeline (CI/CD)

Workflow de GitHub Actions (`.github/workflows/ci-cd.yml`) con 4 jobs encadenados:

| Job | Herramienta | Función |
|---|---|---|
| `test` | Pytest | Corre `test_app.py` contra la app |
| `bandit` | Bandit (SAST) | Analiza `app.py` y `test_app.py` en busca de vulnerabilidades |
| `trivy` | Trivy | Escanea la imagen Docker construida en busca de vulnerabilidades CRITICAL/HIGH |
| `deploy` | appleboy/ssh-action | Conecta por SSH a la instancia EC2 y despliega (`git pull` + `docker compose up --build -d`) |

**Secrets configurados en GitHub** (Settings → Secrets and variables → Actions):
- `EC2_HOST` — IP pública/elástica de la instancia
- `EC2_USER` — usuario SSH (`ubuntu`)
- `EC2_SSH_KEY` — llave privada de acceso

**Estado final:** los 4 jobs (Pytest, Bandit, Trivy, Deploy a EC2) corren en verde en cada push a `main`.

---

## Fase 4 — Despliegue en EC2

### Infraestructura de servidor
- Instancia EC2 (Ubuntu 22.04, tipo `t3.micro`) con Docker instalado vía script oficial
- **Dirección IP elástica** asignada (fija, no cambia al reiniciar la instancia)
- Security Group configurado:
  - Entrada: puertos 22 (SSH), 80 (HTTP), 443 (HTTPS), 81 (admin NPM), 5050 (app) — origen `0.0.0.0/0`
  - Salida: todo el tráfico permitido (`0.0.0.0/0`)

### Proxy reverso y dominio
- Dominio gratuito vía **DuckDNS**: `heidyaudit1.duckdns.org` (+ 2 subdominios adicionales para los servicios de monitoreo)
- **Nginx Proxy Manager** configurado con 3 Proxy Hosts:

| Servicio | Dominio | Puerto interno |
|---|---|---|
| API TechNova (app) | [heidyaudit1.duckdns.org](http://heidyaudit1.duckdns.org) | 5050 |
| Dozzle (logs) | [heidyaudit1-dozzle.duckdns.org](http://heidyaudit1-dozzle.duckdns.org) | 8080 |
| Uptime Kuma (monitoreo) | [heidyaudit1-kuma.duckdns.org](http://heidyaudit1-kuma.duckdns.org) | 3001 |

### Servicios de observabilidad
- **Dozzle**: visualización de logs en tiempo real de los 5 contenedores del stack, sin configuración adicional (lee directo del socket de Docker)
- **Uptime Kuma**: monitor HTTP configurado contra `http://app:5050/health`, capturando el comportamiento real de la app (incluye el fallo simulado del 30% programado en el endpoint, reflejado en el uptime ~70-80% y en el historial Up/Down)

### `docker-compose.yml` final (5 servicios)
```yaml
services:
  app:
    build: .
    restart: unless-stopped
    env_file: .env
    ports:
      - "5050:5050"
    depends_on:
      - db

  db:
    image: mysql:8.0
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASS}
      MYSQL_DATABASE: ${DB_NAME}
    volumes:
      - db_data:/var/lib/mysql

  nginx-proxy-manager:
    image: 'jc21/nginx-proxy-manager:latest'
    restart: unless-stopped
    ports:
      - '80:80'
      - '443:443'
      - '81:81'
    volumes:
      - ./npm/data:/data
      - ./npm/letsencrypt:/etc/letsencrypt

  dozzle:
    image: amir20/dozzle:latest
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

  uptime-kuma:
    image: louislam/uptime-kuma:latest
    restart: unless-stopped
    volumes:
      - ./kuma:/app/data

volumes:
  db_data:
```

---

## Resumen final del proyecto

| Fase | Entregable | Estado |
|---|---|---|
| 1 — Auditoría | `AUDITORIA.md` con hallazgos reales de Bandit | ✅ Completo |
| 2 — Arquitectura | Código refactorizado + `docker-compose.yml` local | ✅ Completo (0 hallazgos en Bandit) |
| 3 — Pipeline | `.github/workflows/ci-cd.yml` (Pytest, Bandit, Trivy, Deploy) | ✅ Completo (4/4 jobs en verde) |
| 4 — Despliegue en EC2 | Proxy + 3 subdominios + monitoreo activo | ✅ Completo |

### Notas de seguridad adicionales
- Las llaves privadas SSH (`.pem`) fueron removidas del control de versiones y agregadas a `.gitignore` tras detectarse que habían sido incluidas accidentalmente en un commit.
- El archivo `.env` con credenciales reales nunca se subió al repositorio (excluido vía `.gitignore` desde la Fase 2).
