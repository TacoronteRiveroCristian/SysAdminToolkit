#!/bin/bash

# Iniciar InfluxDB en segundo plano
influxd &
# Guardar PID para luego matar el servicio, sino no se logra matar el servicio
INFLUXDB_PID=$!

# Esperar a que InfluxDB esté listo
until curl -sL -I localhost:8086/ping | grep "HTTP/1.1 204 No Content"; do
  echo "Waiting for InfluxDB to start..."
  sleep 1
done

echo "InfluxDB started"

# Crear el usuario administrador
influx -execute "CREATE USER ${INFLUXDB_ADMIN_USER} WITH PASSWORD '${INFLUXDB_ADMIN_PASSWORD}' WITH ALL PRIVILEGES"

# Detener InfluxDB
kill $INFLUXDB_PID

# Esperar a que InfluxDB se detenga para modificar sus archivos
wait $INFLUXDB_PID

echo "Admin User created!"

# Añadir o modificar la sección [http] según el valor de INFLUXDB_HTTP_AUTH_ENABLED
if [ "${INFLUXDB_HTTP_AUTH_ENABLED}" = "true" ]; then
  if ! grep -q "\[http\]" /etc/influxdb/influxdb.conf; then
    echo -e "\n[http]\n  auth-enabled = true" >> /etc/influxdb/influxdb.conf
  else
    # sed -i modifica texto in situ
    # s/.../.../ es patron/comando de reemplazo
    # se busca # auth-enabled = false y se reemplaza con # auth-enabled = true
    # y finalmente se especifica en que archivo se hace eso
    # Aqui se intenta buscar todas las posibles opciones de auth-enabled y se reemplaza con true
    sed -i 's/# auth-enabled = false/auth-enabled = true/' /etc/influxdb/influxdb.conf
    sed -i 's/auth-enabled = false/auth-enabled = true/' /etc/influxdb/influxdb.conf
    sed -i 's/# auth-enabled = true/auth-enabled = true/' /etc/influxdb/influxdb.conf
  fi
  echo "InfluxDB authentication enabled."
else
  if ! grep -q "\[http\]" /etc/influxdb/influxdb.conf; then
    echo -e "\n[http]\n  # auth-enabled = false" >> /etc/influxdb/influxdb.conf
  else
    sed -i 's/auth-enabled = true/# auth-enabled = false/' /etc/influxdb/influxdb.conf
    sed -i 's/auth-enabled = false/# auth-enabled = false/' /etc/influxdb/influxdb.conf
    sed -i 's/# auth-enabled = true/# auth-enabled = false/' /etc/influxdb/influxdb.conf
  fi
  echo "InfluxDB authentication disabled."
fi

echo "InfluxDB configuration updated!"

# Iniciar InfluxDB con autenticación habilitada
# (Reiniciar influxd para que los archivos de configuración se actualicen)
exec influxd