# Sistema de Testing - InfluxDB Backup Toolkit

Sistema completo de testing para verificar la integridad y calidad del proceso de backup de InfluxDB mediante tests unitarios, de integración y validación de datos masivos.

## Estructura del Sistema de Testing

```
test/
├── README.md               # Este archivo
├── conftest.py            # Configuración global pytest
├── requirements-test.txt   # Dependencias de testing
├── run_tests.py           # Script principal para ejecutar tests
├── __init__.py
├── unit/                  # Tests unitarios
│   ├── test_data_generator.py      # Tests del generador de datos
│   ├── test_quality_metrics.py     # Tests de métricas de calidad
│   ├── test_influxdb_client.py     # Tests del cliente InfluxDB
│   └── __init__.py
├── integration/           # Tests de integración
│   ├── test_full_backup_cycle.py   # Tests de ciclo completo
│   └── __init__.py
├── data/                  # Generadores de datos heterogéneos
│   ├── data_generator.py          # Generador principal
│   ├── test_datasets.py           # Datasets predefinidos
│   └── __init__.py
├── utils/                 # Utilidades de testing
│   ├── quality_metrics.py         # Sistema de métricas de calidad
│   ├── influxdb_test_helper.py     # Helper para InfluxDB
│   └── __init__.py
├── config/                # Configuraciones de testing
├── docker/                # Infraestructura Docker para testing
│   ├── docker-compose.test.yml     # Servicios InfluxDB para testing
│   ├── Dockerfile.test            # Contenedor de testing
│   ├── influxdb_source.conf       # Config InfluxDB origen
│   ├── influxdb_destination.conf  # Config InfluxDB destino
│   └── influxdb_extra.conf        # Config InfluxDB adicional
└── results/               # Resultados de tests (generado)
```

## Inicio Rápido

### 1. Prerrequisitos

```bash
# Tener Docker y Docker Compose instalados
docker --version
docker-compose --version

# Python 3.8+ (para ejecución local)
python --version
```

### 2. Instalar Dependencias de Testing

```bash
# Desde la raíz del proyecto
pip install -r test/requirements-test.txt
```

### 3. Levantar Servicios de Testing

```bash
# Levantar servidores InfluxDB para testing
cd test/docker
docker-compose -f docker-compose.test.yml up -d

# Verificar que están activos
docker-compose -f docker-compose.test.yml ps
```

**Servicios disponibles:**
- **InfluxDB Source**: `http://localhost:8086` (servidor origen)
- **InfluxDB Destination**: `http://localhost:8087` (servidor destino)
- **InfluxDB Extra**: `http://localhost:8088` (servidor adicional)

### 4. Ejecutar Tests

```bash
# Volver a la raíz del proyecto
cd ../..

# Ejecutar todos los tests
python test/run_tests.py

# Solo tests unitarios
python test/run_tests.py --unit-only

# Solo generar datos de demostración
python test/run_tests.py --demo-data-only

# Omitir tests que requieren Docker
python test/run_tests.py --no-docker
```

## Tipos de Tests

### 1. Tests Unitarios (`test/unit/`)

**Propósito**: Verificar funcionamiento de componentes individuales usando mocks.

#### `test_data_generator.py`
- **Distribuciones numéricas**: Normal, uniforme, exponencial, lineal, estacional
- **Datos booleanos**: Con probabilidades configurables
- **Datos de cadenas**: Aleatorias, nombres, emails, UUIDs, enumeraciones
- **Series temporales**: Con intervalos y jitter configurables
- **Inyección de anomalías**: Outliers, valores faltantes, picos
- **Reproducibilidad**: Verificación con semillas

```bash
# Ejecutar solo tests del generador
python -m pytest test/unit/test_data_generator.py -v
```

#### `test_quality_metrics.py`
- **Métricas numéricas**: Media, mediana, desviación estándar, percentiles
- **Métricas booleanas**: Conteos y proporciones
- **Métricas de cadenas**: Valores únicos, longitudes, distribuciones
- **Métricas temporales**: Rangos de tiempo, verificación de secuencias
- **Tolerancias**: Configuración y validación de tolerancias
- **Exportación**: JSON y HTML

```bash
# Ejecutar solo tests de métricas de calidad
python -m pytest test/unit/test_quality_metrics.py -v
```

#### `test_influxdb_client.py`
- **Conexión**: Test de conectividad con mocks
- **Operaciones CRUD**: Crear bases de datos, escribir y consultar datos
- **Metadatos**: Obtener mediciones, campos, tags
- **Manejo de errores**: Timeouts, errores de autenticación, errores de consulta
- **Configuración**: Autenticación, SSL, timeouts

```bash
# Ejecutar solo tests del cliente InfluxDB
python -m pytest test/unit/test_influxdb_client.py -v
```

### 2. Tests de Integración (`test/integration/`)

**Propósito**: Verificar funcionamiento con servidores InfluxDB reales.

#### `test_full_backup_cycle.py`

**Ciclos de Backup Completos:**
- **Dataset IoT**: Sensores de temperatura, movimiento, medidores de energía
- **Dataset Web Analytics**: Vistas de página, sesiones, llamadas API
- **Dataset System Monitoring**: CPU, memoria, disco
- **Dataset Financial Trading**: Precios, operaciones, métricas de portfolio
- **Dataset E-commerce**: Pedidos, vistas de productos, inventario

**Tests de Rendimiento:**
- **Datasets grandes**: Generación y procesamiento de datos masivos
- **Medición de tiempo**: Verificación de rendimiento
- **Tasa de transferencia**: Registros por segundo

**Verificación de Calidad:**
- **Integridad de datos**: Comparación estadística origen-destino
- **Conteos de registros**: Verificación exacta de cantidades
- **Tipos de datos**: Preservación de tipos
- **Rangos temporales**: Verificación de timestamps

```bash
# Ejecutar solo tests de integración
python -m pytest test/integration/ -m integration -v

# Test específico de ciclo completo
python -m pytest test/integration/test_full_backup_cycle.py::TestFullBackupCycle::test_iot_dataset_backup_cycle -v
```

## Datasets de Prueba

### Datasets Predefinidos

El sistema incluye 5 datasets realistas para testing:

#### 1. **IoT (Internet of Things)**
- **Mediciones**: `temperature_sensors`, `motion_sensors`, `power_meters`
- **Campos**: Temperatura, humedad, presión, nivel de batería, detección de movimiento
- **Tags**: sensor_id, location, floor, room, sensitivity
- **Características**: Patrones estacionales, valores booleanos, datos exponenciales

#### 2. **Web Analytics**
- **Mediciones**: `page_views`, `user_sessions`, `api_calls`
- **Campos**: Tiempo de respuesta, código de estado, bytes enviados, duración de sesión
- **Tags**: URL, método HTTP, user agent, país, fuente
- **Características**: Distribuciones exponenciales, enumeraciones complejas

#### 3. **System Monitoring**
- **Mediciones**: `cpu_usage`, `memory_usage`, `disk_usage`
- **Campos**: Porcentaje de uso, bytes usados/libres, IOPS, bytes por segundo
- **Tags**: host, datacenter, environment, device, mount point
- **Características**: Tendencias lineales, datos de gran volumen

#### 4. **Financial Trading**
- **Mediciones**: `stock_prices`, `trades`, `portfolio_metrics`
- **Campos**: Precio, volumen, bid/ask, P&L, ratios financieros
- **Tags**: símbolo, exchange, trader_id, estrategia
- **Características**: Datos de alta frecuencia, valores monetarios

#### 5. **E-commerce**
- **Mediciones**: `orders`, `product_views`, `inventory`
- **Campos**: Monto de orden, duración de vista, nivel de stock, precios
- **Tags**: product_id, customer_id, categoría, método de pago
- **Características**: UUIDs, datos de comercio electrónico

### Personalizar Datasets

```python
# Ejemplo de dataset personalizado
custom_dataset = {
    "my_measurement": {
        "interval": "30s",
        "fields": {
            "temperature": {"type": "normal", "mean": 25.0, "std": 5.0},
            "active": {"type": "boolean", "true_probability": 0.8}
        },
        "tags": {
            "location": {"type": "enum", "values": ["room1", "room2", "room3"]}
        }
    }
}
```

## Sistema de Métricas de Calidad

### Métricas Implementadas

#### Datos Numéricos
- **Estadísticas básicas**: Media, mediana, desviación estándar
- **Percentiles**: P25, P50, P75, P90, P95, P99
- **Valores extremos**: Mínimo, máximo
- **Tolerancias**: Configurables con errores relativos

#### Datos Booleanos
- **Conteos**: True/False exactos
- **Proporciones**: Ratios con tolerancias

#### Datos de Cadenas
- **Valores únicos**: Conteo y comparación
- **Longitudes**: Promedio y distribución
- **Distribución**: Top 10 valores más frecuentes

#### Datos Temporales
- **Rangos**: Verificación de min/max timestamps
- **Secuencias**: Validación de ordenamiento temporal
- **Tolerancia temporal**: ±1 segundo por defecto

### Configuración de Tolerancias

```python
# Tolerancia estricta (0.1%)
quality_metrics = QualityMetrics(tolerance=0.001)

# Tolerancia normal (1%)
quality_metrics = QualityMetrics(tolerance=0.01)

# Tolerancia relajada (10%)
quality_metrics = QualityMetrics(tolerance=0.1)
```

## Infraestructura Docker

### Servicios de Testing

El archivo `test/docker/docker-compose.test.yml` proporciona:

#### InfluxDB Source (`localhost:8086`)
- **Propósito**: Servidor origen para tests
- **Base de datos**: `test_db`
- **Configuración**: Optimizada para escritura rápida

#### InfluxDB Destination (`localhost:8087`)
- **Propósito**: Servidor destino para tests
- **Base de datos**: `test_db_backup`
- **Configuración**: Optimizada para verificación

#### InfluxDB Extra (`localhost:8088`)
- **Propósito**: Tests avanzados y casos especiales
- **Base de datos**: `extra_test_db`
- **Configuración**: Para tests de múltiples destinos

### Comandos Docker

```bash
# Levantar solo servicios de testing
docker-compose -f test/docker/docker-compose.test.yml up -d

# Ver logs de servicios
docker-compose -f test/docker/docker-compose.test.yml logs -f

# Parar servicios
docker-compose -f test/docker/docker-compose.test.yml down

# Limpiar datos de testing
docker-compose -f test/docker/docker-compose.test.yml down -v
```

## Resultados y Reportes

### Estructura de Resultados

```
test_results/
├── test_report.json           # Reporte JSON completo
├── test_report.html           # Reporte HTML visual
├── unit_tests.json           # Resultados tests unitarios
├── integration_tests.json    # Resultados tests integración
├── coverage_html/            # Reporte de cobertura HTML
├── coverage.json            # Datos de cobertura JSON
└── demo_data/               # Datos de demostración
    ├── datasets_summary.json
    ├── iot_sample.json
    ├── web_analytics_sample.json
    └── ...
```

### Interpretación de Resultados

#### Reporte de Éxito
```json
{
  "summary": {
    "total_tests": 5,
    "successful_tests": 5,
    "failed_tests": 0,
    "success_rate": 1.0,
    "total_duration": 45.2
  }
}
```

#### Reporte de Métricas de Calidad
```json
{
  "measurement_name": "temperature_sensors",
  "total_metrics": 28,
  "passed_metrics": 27,
  "failed_metrics": 1,
  "success_rate": 0.964,
  "summary": {
    "missing_fields": [],
    "extra_fields": [],
    "total_fields": 4
  }
}
```

## Solución de Problemas

### Servicios Docker no inician

```bash
# Verificar puertos ocupados
netstat -tlnp | grep -E ':808[6-8]'

# Limpiar contenedores existentes
docker-compose -f test/docker/docker-compose.test.yml down -v
docker system prune -f

# Volver a levantar
docker-compose -f test/docker/docker-compose.test.yml up -d
```

### Tests fallan por timeout

```bash
# Aumentar timeouts en variables de entorno
export INFLUXDB_TIMEOUT=60
export TEST_TIMEOUT=300

# Verificar conectividad
curl http://localhost:8086/ping
curl http://localhost:8087/ping
```

### Problemas de dependencias

```bash
# Reinstalar dependencias
pip uninstall -r test/requirements-test.txt -y
pip install -r test/requirements-test.txt

# Verificar versiones
python -c "import pytest, numpy, pandas, faker; print('Dependencias OK')"
```

### Limpiar datos de testing

```bash
# Limpiar todo y empezar de nuevo
docker-compose -f test/docker/docker-compose.test.yml down -v
rm -rf test_results/
python test/run_tests.py --unit-only  # Solo unitarios primero
```

## Marcadores pytest

### Marcadores Disponibles

- `@pytest.mark.integration`: Tests que requieren servicios reales
- `@pytest.mark.docker`: Tests que requieren Docker
- `@pytest.mark.slow`: Tests que tardan más tiempo

### Ejecutar por Marcadores

```bash
# Solo tests unitarios (sin marcadores)
python -m pytest test/unit/ -v

# Solo tests de integración
python -m pytest -m integration -v

# Solo tests que requieren Docker
python -m pytest -m docker -v

# Omitir tests lentos
python -m pytest -m "not slow" -v

# Combinaciones
python -m pytest -m "integration and not slow" -v
```

## Casos de Uso Específicos

### Testing de Backup Incremental

```bash
# Test específico para modo incremental
python -m pytest test/integration/test_full_backup_cycle.py::TestFullBackupCycle::test_iot_dataset_backup_cycle -v
```

### Testing de Grandes Volúmenes

```bash
# Test de rendimiento con datasets grandes
python -m pytest test/integration/test_full_backup_cycle.py::TestFullBackupCycle::test_large_dataset_performance -v
```

### Verificación de Calidad de Datos

```bash
# Test específico de métricas de calidad
python -m pytest test/integration/test_full_backup_cycle.py::TestFullBackupCycle::test_data_quality_verification -v
```

### Generar Solo Datos de Demostración

```bash
# Crear datasets de ejemplo sin ejecutar tests
python test/run_tests.py --demo-data-only

# Ver los datos generados
ls -la test_results/demo_data/
```

## Ejemplo de Test Personalizado

```python
# test/integration/test_custom_backup.py
import pytest
from test.utils.influxdb_test_helper import InfluxDBTestHelper
from test.data.test_datasets import get_dataset_config

@pytest.mark.integration
@pytest.mark.docker
class TestCustomBackup:
    def test_my_custom_dataset(self):
        helper = InfluxDBTestHelper()

        # Dataset personalizado
        custom_config = {
            "my_measurement": {
                "interval": "1m",
                "fields": {
                    "value": {"type": "normal", "mean": 100, "std": 10}
                },
                "tags": {
                    "location": {"type": "enum", "values": ["A", "B", "C"]}
                }
            }
        }

        with helper.test_environment(["custom_db", "custom_db_backup"]):
            # Generar y verificar datos
            result = helper.run_full_test_cycle(
                db_name="custom_db",
                dataset_config=custom_config,
                duration_hours=1
            )

            assert result["success"], "Custom backup cycle failed"
```

## Automatización CI/CD

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Testing
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: pip install -r test/requirements-test.txt

      - name: Start InfluxDB services
        run: docker-compose -f test/docker/docker-compose.test.yml up -d

      - name: Wait for services
        run: sleep 30

      - name: Run tests
        run: python test/run_tests.py

      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: test_results/
```

---

## Soporte

Para problemas específicos del sistema de testing:

1. **Verificar logs**: `docker-compose -f test/docker/docker-compose.test.yml logs`
2. **Comprobar conectividad**: `curl http://localhost:8086/ping`
3. **Ejecutar tests unitarios primero**: `python test/run_tests.py --unit-only`
4. **Revisar reportes generados**: `test_results/test_report.html`

**El sistema de testing está diseñado para ser robusto, reproducible y exhaustivo, proporcionando confianza completa en la integridad del proceso de backup.**
