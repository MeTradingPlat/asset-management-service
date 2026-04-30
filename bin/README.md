# Asset Management Service

Microservicio de gestión de activos para la plataforma **MeTradingPlat**. Gestiona el estado de los activos monitoreados, su ciclo de vida y las señales de trading asociadas.

## Tabla de Contenido

- [Arquitectura](#arquitectura)
- [Tecnologías](#tecnologías)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [API Endpoints](#api-endpoints)
- [Kafka Topics](#kafka-topics)
- [Configuración](#configuración)
- [Ejecución](#ejecución)

## Arquitectura

El servicio implementa **Arquitectura Hexagonal** (Puertos y Adaptadores), separando claramente las capas de dominio, aplicación e infraestructura.

```
┌─────────────────────────────────────────────────────────┐
│                Asset Management Service                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │ REST API     │      │ Kafka        │                │
│  │ /activos     │      │ Listeners    │                │
│  └──────┬───────┘      └──────┬───────┘                │
│         │                     │                         │
│         ▼                     ▼                         │
│  ┌────────────────────────────────┐                    │
│  │    Use Cases (Domain Layer)     │                    │
│  │  - Gestionar Activos            │                    │
│  │  - Procesar Señales             │                    │
│  └────────────────────────────────┘                    │
│         │                                                │
│         ▼                                                │
│  ┌────────────────────────────────┐                    │
│  │    PostgreSQL Database          │                    │
│  │  - bd_activos                   │                    │
│  └────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

## Tecnologías

| Tecnología | Versión | Propósito |
|---|---|---|
| Java | 21 | Lenguaje principal |
| Spring Boot | 3.x | Framework |
| Spring Cloud | 2025.0.0 | Eureka client |
| Spring Kafka | - | Mensajería asíncrona |
| PostgreSQL | 15 | Base de datos |
| MapStruct | - | Mapeo DTO <-> Dominio |
| Lombok | - | Reducción de boilerplate |
| Docker | Multi-stage | Contenedorización |

## Estructura del Proyecto

```
src/main/java/com/metradingplat/asset_management/
├── application/
│   ├── input/                    # Puertos de entrada (interfaces)
│   └── output/                   # Puertos de salida (interfaces)
├── domain/
│   ├── models/                   # Modelos de dominio
│   │   ├── Activo.java
│   │   └── Signal.java
│   └── usecases/                 # Implementación de casos de uso
└── infrastructure/
    ├── configuration/            # Beans y configuración Spring
    ├── input/
    │   ├── controllerGestionarActivo/
    │   │   ├── controller/       # REST Controller
    │   │   ├── DTOAnswer/        # DTOs de respuesta
    │   │   └── mapper/           # MapStruct mappers
    │   ├── kafkaGestionarActivo/
    │   │   └── listener/         # Kafka listeners (asset-state)
    │   └── kafkaGestionarSignals/
    │       └── listener/         # Kafka listeners (signals)
    └── output/
        └── persistence/          # JPA repositories
```

## API Endpoints

Base path: `/api/activos`

| Método | Path | Descripción |
|---|---|---|
| `GET` | `/activos` | Listar todos los activos |
| `GET` | `/activos/{id}` | Obtener activo por ID |
| `POST` | `/activos` | Crear nuevo activo |
| `PUT` | `/activos/{id}` | Actualizar activo |
| `DELETE` | `/activos/{id}` | Eliminar activo |

### Ejemplos

**Obtener todos los activos:**
```bash
GET /api/activos
```

**Crear nuevo activo:**
```json
POST /api/activos
{
  "symbol": "AAPL",
  "status": "ACTIVE",
  "scanners": ["momentum", "breakout"]
}
```

## Kafka Topics

### Consumidos (Input)

| Topic | Productor | Descripción |
|---|---|---|
| `signals` | signal-processing-service | Señales de trading detectadas por scanners |
| `asset-state` | signal-processing-service | Cambios de estado de activos monitoreados |

### Publicados (Output)

Este servicio actualmente no publica a topics de Kafka (solo consume).

## Configuración

### Variables de Entorno

| Variable | Descripción |
|---|---|
| `DB_HOST` | Host de PostgreSQL (default: `postgres-activos`) |
| `DB_PORT` | Puerto de PostgreSQL (default: `5432`) |
| `DB_NAME` | Nombre de la base de datos (default: `bd_activos`) |
| `POSTGRES_USER` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL |
| `KAFKA_BOOTSTRAP_SERVERS` | Servidor Kafka (default: `kafka:29092`) |
| `EUREKA_HOST` | Host del servidor Eureka (default: `directory`) |

### Perfiles de Spring

- **dev**: Base de datos local, Kafka en localhost:9092, logging DEBUG
- **prod**: Configuración via variables de entorno (Docker)

## Ejecución

### Con Docker (recomendado)

El servicio se despliega automáticamente via CI/CD cuando se hace push a la rama `master`.

Ver estado del contenedor:
```bash
docker ps | grep asset-management-service
docker logs -f asset-management-service
```

### Desarrollo Local

```bash
cd asset-management-service

# Configurar variables de entorno
export DB_HOST=localhost
export DB_PORT=5435
export POSTGRES_USER=user_activos
export POSTGRES_PASSWORD=tu_password

mvn spring-boot:run -Dspring-boot.run.profiles=dev
```

### Servicios Relacionados

| Servicio | Puerto | Descripción |
|---|---|---|
| PostgreSQL (activos) | 5435 | Base de datos de este servicio |
| Directory (Eureka) | 8761 | Service registry |
| Gateway | 8080 | API Gateway |
| **asset-management-service** | **8083** | **Este servicio** |
| signal-processing-service | 8000 | Generador de señales |

## Base de Datos

### Conexión

```
Host: postgres-activos
Port: 5432 (interno) / 5435 (externo)
Database: bd_activos
User: user_activos
```

### Esquema

El servicio usa JPA/Hibernate para gestionar automáticamente el esquema de la base de datos.

Entidades principales:
- `Activo`: Activos monitoreados con su estado y configuración
- (Otras entidades según tu implementación)

## Integración con otros servicios

```
signal-processing-service → [Kafka: signals] → asset-management-service
signal-processing-service → [Kafka: asset-state] → asset-management-service
```

## Health Check

El servicio expone actuadores de Spring Boot:

```bash
GET http://localhost:8083/actuator/health
```
