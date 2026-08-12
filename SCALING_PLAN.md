# 🚀 Plan de Escalabilidad y Hoja de Ruta Enterprise: Tempus DDB

**Proyecto:** Tempus DDB — Infraestructura de Seguridad B2A (Business-to-Agent & Agent-to-Agent)  
**Versión Actual:** v0.2.1 (Slice Vertical Local)  
**Objetivo:** Transición de Ledger Local a Plataforma Distribuida de Alta Disponibilidad y Seguridad Enterprise.

---

## 📐 Visión de Arquitectura a Escala

```text
  ┌───────────────────────┐
  │ Workload Autónoma     │
  │ (Agente IA / Service) │
  └───────────┬───────────┘
              │ 1. Signed Intent (Ed25519)
              ▼
┌───────────────────────────────┐
│     Tempus Gate Cluster       │
│  (Load Balanced / Auto-Scale) │
│  - Identity & Policy Engine   │
│  - Idempotency & Replay Store │
│  - Cloud KMS / HSM Signer     │
└─────────────┬─────────────────┘
              │ 2. Single-use Expiring Permit
              ▼
┌───────────────────────────────┐
│      Mediated Executor        │
│   (Proxy HTTP / DB / API)     │
│  - Holds API Keys / Tokens    │
│  - Consumes Permit Atomically │
│  - Executes External Effect   │
└─────────────┬─────────────────┘
              │ 3. Signed Outcome
              ▼
┌───────────────────────────────┐
│  Distributed Receipt Store    │
│  - NATS JetStream / Kafka     │
│  - Merkle Transparency Tree   │
│  - External Checkpointing     │
└─────────────┬─────────────────┘
              │ 4. Verifiable Trace
              ▼
┌───────────────────────────────┐
│   Read-only Audit Console     │
│   (Web Dashboard & SIEM)      │
└───────────────────────────────┘
```

---

## 🗓️ Fases de Escalabilidad

### 📍 Fase 1: Optimización de Almacenamiento Local (10k-50k ops/sec)
*Estado: Implementado parcialmente en v0.2.1 (WAL Mode + Performance Profile).*

- [x] **SQLite WAL Mode & PRAGMA Performance:** Configurar `journal_mode = WAL`, `synchronous = NORMAL` y `busy_timeout = 5000`.
- [x] **Caché en Memoria de Llaves:** Eliminar lecturas redundantes a disco de `keys.json` mediante caching en memoria (`RefCell<Option<SigningKey>>`).
- [ ] **Connection Pooling (Rust):** Implementar un pool de conexiones SQLite utilizando `r2d2` o `deadpool-sqlite` en `SqliteExecutorStorage` para eliminar la sobrecarga de apertura de conexiones por solicitud.
- [ ] **Validación y Exportación Streaming:** Reemplazar la carga total de filas a memoria en `validate_ledger()` y `export_ledger()` por iteradores streaming y serialización paginada para manejar millones de registros sin impacto de memoria (OOM).

---

### 📍 Fase 2: Adaptadores de Ejecutor Mediado Out-of-the-Box
*Objetivo: Convertir Tempus en una barrera infranqueable de seguridad donde el Agente jamás posea las credenciales finales.*

- [ ] **Proxy HTTP / Reverse Proxy:**
  - Crear un proxy reverse transparente en Rust (usando `hyper` / `axum`) que intercepte peticiones HTTP de agentes hacia APIs externas.
  - El proxy valida el permiso Tempus antes de adjuntar la cabecera `Authorization: Bearer <SECRET_TOKEN>` real.
- [ ] **Adaptador de Base de Datos (PostgreSQL / MySQL / Redis):**
  - Proxy mediador para queries destructivas o de alto valor (`UPDATE`, `DELETE`, `DROP`).
- [ ] **Adaptador Web3 / Wallets Cripto:**
  - Mediador para firmas de transacciones en blockchain que solo firma y transmite si existe un permiso Tempus `ALLOWED` válido.

---

### 📍 Fase 3: Identidad Enterprise, KMS y Gestión de Llaves
*Objetivo: Eliminar completamente los archivos de llaves en texto plano (`keys.json`) en entornos de producción.*

- [ ] **Integración con HSM y Cloud KMS:**
  - Abstracción de traits en Rust para proveedores de firma: `AWS KMS`, `GCP Cloud KMS`, `Azure Key Vault`, y `HashiCorp Vault`.
  - Firma remota asíncrona mediante llamadas de API del KMS sin exponer llaves privadas.
- [ ] **Workload Identity & OIDC:**
  - Autenticación automática de agentes mediante SPIFFE/SPIRE, Kubernetes Service Account Tokens (JWT), o tokens IAM de la nube.
  - Generación dinámica de certificados/llaves efímeras para agentes sin necesidad de registro manual previo.
- [ ] **Revocación y Rotación de Llaves:**
  - Registro inmutable de eventos de rotación y revocación de llaves de agentes y ejecutores.
  - Verificación histórica retroactiva: los recibos antiguos siguen siendo verificables incluso tras la rotación de llaves del emisor.

---

### 📍 Fase 4: Escalabilidad Horizontal y Ingesta Distribuida
*Objetivo: Soportar arquitecturas multi-región con tolerancia a fallos y auditoría inmune al borrado local.*

- [ ] **Ingesta Distribuida de Eventos (Event Streaming):**
  - Integración con **NATS JetStream**, **Apache Kafka** o **Redpanda** como log de eventos *append-only* de alta velocidad.
  - Desacoplar la recepción de permisos y la persistencia final en base de datos.
- [ ] **Log de Transparencia Merkle (Certificate Transparency pattern):**
  - Construcción de árboles de Merkle en tiempo real sobre los recibos de ejecución.
  - Publicación periódica del *Merkle Root* en checkpoints externos (ej: IPFS, Ethereum, o buckets S3 WORM en modo compliance).
  - **Detección de Borrado/Rollback:** Si un atacante borra la base de datos local, la discrepancia contra el Merkle Root público es detectada inmediatamente.
- [ ] **Aislamiento Multi-Tenant y Quotas:**
  - Separación lógica/física de esquemas de datos por `tenant_id`.
  - Rate-limiting integrado por agente, tenant y tipo de recurso.

---

### 📍 Fase 5: Consola de Auditoría Web y Ecosistema de SDKs
*Objetivo: Facilitar la observabilidad para auditores humanos e integrar Tempus en cualquier lenguaje.*

- [ ] **Dashboard de Auditoría (Web Console):**
  - Aplicación Next.js / Tailwind CSS de **solo lectura**.
  - Visualización gráfica de la línea de tiempo de decisiones autónomas.
  - Filtros avanzados por tenant, agente, nivel de riesgo, resultado (`SUCCEEDED` / `FAILED`) y metadatos financieros.
  - Verificador gráfico de firmas criptográficas (un clic para validar toda la cadena de una transacción).
- [ ] **Integración con SIEM y Observabilidad:**
  - Expostador OpenTelemetry (OTel) para métricas y trazas.
  - Conectores directos para Datadog, Splunk, Elastic y AWS CloudWatch.
- [ ] **SDKs Multilenguaje:**
  - **TypeScript / Node.js SDK:** Binding nativo y cliente API.
  - **Go SDK:** Cliente ligero para microservicios en Go.
  - **Java / Kotlin SDK:** Para integración en entornos empresariales Java.
  - **WASM Package:** Verificador criptográfico ejecutable 100% en el navegador web del auditor.

---

## 📊 Métricas Clave de Desempeño (KPIs de Escalabilidad)

| Métrica | Meta Corto Plazo | Meta Enterprise (Escala) |
|---|---|---|
| **Latencia de Permiso (`request_action`)** | < 2 ms | < 500 µs |
| **Throughput de Inserción** | 5,000 ops/sec | > 50,000 ops/sec |
| **Tiempo de Verificación de Trace** | < 1 ms por acción | < 100 µs por acción |
| **Concurrencia de Agentes Simultáneos** | 100 | > 10,000 |
| **Disponibilidad del Gate (Uptime)** | 99.9% | 99.999% |

---

## 🔒 Cumplimiento Normativo (Compliance Targets)

Un ledger inmutable y verificable posiciona a Tempus DDB como la capa de cumplimiento ideal para regulaciones de IA:

- **EU AI Act (Artículo 12 - Record-keeping):** Trazabilidad y registro automático de eventos durante todo el ciclo de vida de sistemas de IA de alto riesgo.
- **SOC 2 Type II (Trust Services Criteria - Security & Availability):** Pista de auditoría inalterable para operaciones automatizadas.
- **ISO/IEC 42001 (Artificial Intelligence Management System):** Controles de gobernanza y responsabilidad en decisiones autónomas.
- **HIPAA / PCI-DSS:** Registro inmutable de acceso y modificación de datos sensibles de salud o financieros por parte de agentes.
