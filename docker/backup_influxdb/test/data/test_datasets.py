"""
Configuraciones predefinidas para datasets de testing
====================================================

Conjuntos de datos predefinidos para diferentes escenarios de testing.
"""

from datetime import datetime, timedelta
from typing import Any, Dict

# Dataset de IoT (Internet of Things)
IOT_DATASET = {
    "temperature_sensors": {
        "interval": "30s",
        "fields": {
            "temperature": {
                "type": "seasonal",
                "amplitude": 15.0,
                "period": 1440,
                "offset": 20.0,
                "noise": 0.5,
            },
            "humidity": {"type": "normal", "mean": 60.0, "std": 10.0},
            "pressure": {"type": "normal", "mean": 1013.25, "std": 5.0},
            "battery_level": {
                "type": "linear",
                "start": 100.0,
                "end": 80.0,
                "noise": 0.02,
            },
        },
        "tags": {
            "sensor_id": {
                "type": "enum",
                "values": ["temp_001", "temp_002", "temp_003", "temp_004"],
            },
            "location": {
                "type": "enum",
                "values": ["building_a", "building_b", "building_c"],
            },
            "floor": {
                "type": "enum",
                "values": ["floor_1", "floor_2", "floor_3", "floor_4"],
            },
            "room": {
                "type": "enum",
                "values": ["room_101", "room_102", "room_201", "room_202"],
            },
        },
    },
    "motion_sensors": {
        "interval": "10s",
        "fields": {
            "motion_detected": {"type": "boolean", "true_probability": 0.1},
            "light_level": {"type": "uniform", "low": 0.0, "high": 1000.0},
            "noise_level": {"type": "exponential", "scale": 30.0},
        },
        "tags": {
            "sensor_id": {
                "type": "enum",
                "values": ["motion_001", "motion_002", "motion_003"],
            },
            "location": {
                "type": "enum",
                "values": ["entrance", "hallway", "office", "conference_room"],
            },
            "sensitivity": {
                "type": "enum",
                "values": ["low", "medium", "high"],
            },
        },
    },
    "power_meters": {
        "interval": "1m",
        "fields": {
            "power_consumption": {
                "type": "seasonal",
                "amplitude": 50.0,
                "period": 1440,
                "offset": 100.0,
                "noise": 0.1,
            },
            "voltage": {"type": "normal", "mean": 220.0, "std": 2.0},
            "current": {"type": "normal", "mean": 10.0, "std": 1.5},
            "power_factor": {"type": "uniform", "low": 0.8, "high": 1.0},
        },
        "tags": {
            "meter_id": {
                "type": "enum",
                "values": ["meter_001", "meter_002", "meter_003"],
            },
            "circuit": {
                "type": "enum",
                "values": ["circuit_a", "circuit_b", "circuit_c"],
            },
            "phase": {"type": "enum", "values": ["L1", "L2", "L3"]},
        },
    },
}


# Dataset de aplicaciones web
WEB_ANALYTICS_DATASET = {
    "page_views": {
        "interval": "1s",
        "fields": {
            "response_time": {"type": "exponential", "scale": 200.0},
            "status_code": {
                "type": "enum",
                "values": [200, 200, 200, 200, 200, 404, 500],
            },
            "bytes_sent": {"type": "uniform", "low": 1000, "high": 50000},
            "user_authenticated": {"type": "boolean", "true_probability": 0.3},
        },
        "tags": {
            "url": {
                "type": "enum",
                "values": [
                    "/home",
                    "/products",
                    "/about",
                    "/contact",
                    "/login",
                    "/api/users",
                ],
            },
            "method": {
                "type": "enum",
                "values": ["GET", "POST", "PUT", "DELETE"],
            },
            "user_agent": {
                "type": "enum",
                "values": ["Chrome", "Firefox", "Safari", "Edge", "Mobile"],
            },
            "country": {"type": "country"},
            "source": {
                "type": "enum",
                "values": ["direct", "google", "facebook", "twitter", "email"],
            },
        },
    },
    "user_sessions": {
        "interval": "5m",
        "fields": {
            "session_duration": {"type": "exponential", "scale": 600.0},
            "pages_visited": {"type": "uniform", "low": 1, "high": 20},
            "bounce_rate": {"type": "boolean", "true_probability": 0.4},
            "conversion": {"type": "boolean", "true_probability": 0.02},
        },
        "tags": {
            "user_id": {"type": "uuid"},
            "session_id": {"type": "uuid"},
            "device_type": {
                "type": "enum",
                "values": ["desktop", "mobile", "tablet"],
            },
            "browser": {
                "type": "enum",
                "values": ["Chrome", "Firefox", "Safari", "Edge"],
            },
            "os": {
                "type": "enum",
                "values": ["Windows", "macOS", "Linux", "iOS", "Android"],
            },
        },
    },
    "api_calls": {
        "interval": "100ms",
        "fields": {
            "response_time": {"type": "normal", "mean": 150.0, "std": 50.0},
            "cpu_usage": {"type": "uniform", "low": 0.0, "high": 100.0},
            "memory_usage": {"type": "normal", "mean": 512.0, "std": 100.0},
            "error_rate": {"type": "boolean", "true_probability": 0.01},
        },
        "tags": {
            "endpoint": {
                "type": "enum",
                "values": [
                    "/api/v1/users",
                    "/api/v1/products",
                    "/api/v1/orders",
                ],
            },
            "method": {
                "type": "enum",
                "values": ["GET", "POST", "PUT", "DELETE", "PATCH"],
            },
            "version": {"type": "enum", "values": ["v1", "v2"]},
            "service": {
                "type": "enum",
                "values": ["user-service", "product-service", "order-service"],
            },
            "instance": {
                "type": "enum",
                "values": ["instance-1", "instance-2", "instance-3"],
            },
        },
    },
}


# Dataset de sistema de monitoring
SYSTEM_MONITORING_DATASET = {
    "cpu_usage": {
        "interval": "15s",
        "fields": {
            "usage_percent": {
                "type": "seasonal",
                "amplitude": 30.0,
                "period": 1440,
                "offset": 40.0,
                "noise": 0.1,
            },
            "load_average_1m": {"type": "normal", "mean": 1.5, "std": 0.5},
            "load_average_5m": {"type": "normal", "mean": 1.3, "std": 0.3},
            "load_average_15m": {"type": "normal", "mean": 1.1, "std": 0.2},
        },
        "tags": {
            "host": {
                "type": "enum",
                "values": ["server-01", "server-02", "server-03", "server-04"],
            },
            "cpu_core": {
                "type": "enum",
                "values": ["cpu0", "cpu1", "cpu2", "cpu3"],
            },
            "datacenter": {
                "type": "enum",
                "values": ["dc-us-east", "dc-us-west", "dc-eu-central"],
            },
            "environment": {
                "type": "enum",
                "values": ["prod", "staging", "dev"],
            },
        },
    },
    "memory_usage": {
        "interval": "30s",
        "fields": {
            "used_bytes": {
                "type": "linear",
                "start": 2000000000,
                "end": 6000000000,
                "noise": 0.1,
            },
            "free_bytes": {
                "type": "linear",
                "start": 6000000000,
                "end": 2000000000,
                "noise": 0.1,
            },
            "cached_bytes": {
                "type": "normal",
                "mean": 1000000000,
                "std": 200000000,
            },
            "buffer_bytes": {
                "type": "normal",
                "mean": 500000000,
                "std": 100000000,
            },
        },
        "tags": {
            "host": {
                "type": "enum",
                "values": ["server-01", "server-02", "server-03", "server-04"],
            },
            "datacenter": {
                "type": "enum",
                "values": ["dc-us-east", "dc-us-west", "dc-eu-central"],
            },
            "environment": {
                "type": "enum",
                "values": ["prod", "staging", "dev"],
            },
        },
    },
    "disk_usage": {
        "interval": "1m",
        "fields": {
            "used_bytes": {
                "type": "linear",
                "start": 50000000000,
                "end": 80000000000,
                "noise": 0.05,
            },
            "free_bytes": {
                "type": "linear",
                "start": 50000000000,
                "end": 20000000000,
                "noise": 0.05,
            },
            "read_iops": {"type": "uniform", "low": 100, "high": 1000},
            "write_iops": {"type": "uniform", "low": 50, "high": 500},
            "read_bytes_per_sec": {"type": "exponential", "scale": 1000000},
            "write_bytes_per_sec": {"type": "exponential", "scale": 500000},
        },
        "tags": {
            "host": {
                "type": "enum",
                "values": ["server-01", "server-02", "server-03", "server-04"],
            },
            "device": {
                "type": "enum",
                "values": ["/dev/sda", "/dev/sdb", "/dev/sdc"],
            },
            "mount_point": {
                "type": "enum",
                "values": ["/", "/var", "/tmp", "/home"],
            },
            "filesystem": {"type": "enum", "values": ["ext4", "xfs", "btrfs"]},
        },
    },
}


# Dataset de trading financiero
FINANCIAL_TRADING_DATASET = {
    "stock_prices": {
        "interval": "1s",
        "fields": {
            "price": {"type": "normal", "mean": 100.0, "std": 5.0},
            "volume": {"type": "exponential", "scale": 1000},
            "bid": {"type": "normal", "mean": 99.5, "std": 5.0},
            "ask": {"type": "normal", "mean": 100.5, "std": 5.0},
            "high": {"type": "normal", "mean": 102.0, "std": 5.0},
            "low": {"type": "normal", "mean": 98.0, "std": 5.0},
        },
        "tags": {
            "symbol": {
                "type": "enum",
                "values": ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"],
            },
            "exchange": {"type": "enum", "values": ["NASDAQ", "NYSE", "BATS"]},
            "market_type": {
                "type": "enum",
                "values": ["equity", "option", "future"],
            },
            "currency": {
                "type": "enum",
                "values": ["USD", "EUR", "JPY", "GBP"],
            },
        },
    },
    "trades": {
        "interval": "100ms",
        "fields": {
            "trade_price": {"type": "normal", "mean": 100.0, "std": 5.0},
            "trade_volume": {"type": "uniform", "low": 100, "high": 10000},
            "trade_value": {"type": "normal", "mean": 10000.0, "std": 5000.0},
            "is_buy": {"type": "boolean", "true_probability": 0.5},
        },
        "tags": {
            "symbol": {
                "type": "enum",
                "values": ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"],
            },
            "trader_id": {"type": "uuid"},
            "order_type": {
                "type": "enum",
                "values": ["market", "limit", "stop", "stop_limit"],
            },
            "exchange": {"type": "enum", "values": ["NASDAQ", "NYSE", "BATS"]},
            "side": {"type": "enum", "values": ["buy", "sell"]},
        },
    },
    "portfolio_metrics": {
        "interval": "1m",
        "fields": {
            "total_value": {
                "type": "normal",
                "mean": 1000000.0,
                "std": 50000.0,
            },
            "daily_pnl": {"type": "normal", "mean": 0.0, "std": 10000.0},
            "sharpe_ratio": {"type": "normal", "mean": 1.5, "std": 0.5},
            "max_drawdown": {"type": "uniform", "low": 0.0, "high": 0.2},
            "volatility": {"type": "exponential", "scale": 0.15},
        },
        "tags": {
            "portfolio_id": {"type": "uuid"},
            "strategy": {
                "type": "enum",
                "values": [
                    "momentum",
                    "mean_reversion",
                    "arbitrage",
                    "market_making",
                ],
            },
            "risk_level": {"type": "enum", "values": ["low", "medium", "high"]},
            "asset_class": {
                "type": "enum",
                "values": ["equity", "fixed_income", "commodity", "forex"],
            },
        },
    },
}


# Dataset de e-commerce
ECOMMERCE_DATASET = {
    "orders": {
        "interval": "2m",
        "fields": {
            "order_amount": {"type": "exponential", "scale": 50.0},
            "item_count": {"type": "uniform", "low": 1, "high": 10},
            "shipping_cost": {"type": "normal", "mean": 8.99, "std": 2.0},
            "tax_amount": {"type": "normal", "mean": 5.0, "std": 2.0},
            "discount_applied": {"type": "boolean", "true_probability": 0.3},
        },
        "tags": {
            "order_id": {"type": "uuid"},
            "customer_id": {"type": "uuid"},
            "product_category": {
                "type": "enum",
                "values": [
                    "electronics",
                    "clothing",
                    "books",
                    "home",
                    "sports",
                ],
            },
            "payment_method": {
                "type": "enum",
                "values": [
                    "credit_card",
                    "paypal",
                    "apple_pay",
                    "bank_transfer",
                ],
            },
            "shipping_method": {
                "type": "enum",
                "values": ["standard", "express", "overnight", "pickup"],
            },
            "country": {"type": "country"},
        },
    },
    "product_views": {
        "interval": "5s",
        "fields": {
            "view_duration": {"type": "exponential", "scale": 30.0},
            "page_depth": {"type": "uniform", "low": 1, "high": 5},
            "add_to_cart": {"type": "boolean", "true_probability": 0.05},
            "add_to_wishlist": {"type": "boolean", "true_probability": 0.02},
        },
        "tags": {
            "product_id": {"type": "uuid"},
            "user_id": {"type": "uuid"},
            "category": {
                "type": "enum",
                "values": [
                    "electronics",
                    "clothing",
                    "books",
                    "home",
                    "sports",
                ],
            },
            "brand": {
                "type": "enum",
                "values": ["BrandA", "BrandB", "BrandC", "BrandD", "BrandE"],
            },
            "price_range": {
                "type": "enum",
                "values": ["0-25", "25-50", "50-100", "100-250", "250+"],
            },
            "source": {
                "type": "enum",
                "values": ["search", "category", "recommendation", "promotion"],
            },
        },
    },
    "inventory": {
        "interval": "5m",
        "fields": {
            "stock_level": {
                "type": "linear",
                "start": 100,
                "end": 20,
                "noise": 0.1,
            },
            "reorder_point": {"type": "uniform", "low": 10, "high": 50},
            "cost_per_unit": {"type": "normal", "mean": 25.0, "std": 10.0},
            "selling_price": {"type": "normal", "mean": 50.0, "std": 20.0},
        },
        "tags": {
            "product_id": {"type": "uuid"},
            "warehouse": {
                "type": "enum",
                "values": ["warehouse_a", "warehouse_b", "warehouse_c"],
            },
            "supplier": {
                "type": "enum",
                "values": ["supplier_1", "supplier_2", "supplier_3"],
            },
            "category": {
                "type": "enum",
                "values": [
                    "electronics",
                    "clothing",
                    "books",
                    "home",
                    "sports",
                ],
            },
            "sku": {"type": "random", "length": 8},
        },
    },
}


# Configuración de datasets disponibles
AVAILABLE_DATASETS = {
    "iot": IOT_DATASET,
    "web_analytics": WEB_ANALYTICS_DATASET,
    "system_monitoring": SYSTEM_MONITORING_DATASET,
    "financial_trading": FINANCIAL_TRADING_DATASET,
    "ecommerce": ECOMMERCE_DATASET,
}


def get_dataset_config(dataset_name: str) -> Dict[str, Any]:
    """
    Obtiene la configuración de un dataset predefinido.

    Args:
        dataset_name: Nombre del dataset

    Returns:
        Dict: Configuración del dataset
    """
    if dataset_name not in AVAILABLE_DATASETS:
        raise ValueError(
            f"Dataset '{dataset_name}' no disponible. Disponibles: {list(AVAILABLE_DATASETS.keys())}"
        )

    return AVAILABLE_DATASETS[dataset_name]


def get_available_datasets() -> Dict[str, str]:
    """
    Obtiene la lista de datasets disponibles con sus descripciones.

    Returns:
        Dict: Diccionario con nombres y descripciones
    """
    return {
        "iot": "Sensores IoT (temperatura, movimiento, medidores de energía)",
        "web_analytics": "Analíticas web (vistas de página, sesiones, llamadas API)",
        "system_monitoring": "Monitoreo de sistema (CPU, memoria, disco)",
        "financial_trading": "Trading financiero (precios, operaciones, métricas)",
        "ecommerce": "E-commerce (pedidos, vistas de productos, inventario)",
    }
