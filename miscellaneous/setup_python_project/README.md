# Configuración del Entorno de Desarrollo en Python

Este documento proporciona instrucciones para configurar un entorno de desarrollo en Python utilizando varias herramientas para asegurar la calidad del código. Las herramientas incluidas son `black`, `isort`, `mypy`, `pylint`, y `pre-commit`.

## Herramientas

- **Black** es un formateador de código automático para Python. Es una herramienta opinada que formatea tu código de acuerdo a un estilo consistente y predefinido.
- **Isort**: es una herramienta que ordena automáticamente las importaciones en tus archivos Python según las convenciones de estilo configuradas.
- **MyPy**: es un verificador de tipos para Python. Permite añadir anotaciones de tipo a tu código y verificarlas estáticamente para encontrar posibles errores.
- **Pylint**: es una herramienta para analizar el código fuente en busca de errores y asegurar que sigue las convenciones de estilo de Python.
- **Pre-commit**: es un framework para gestionar y mantener hooks de pre-commit. Estos hooks se ejecutan automáticamente antes de cada commit para verificar y limpiar el código.

## Instalación

Para instalar estas herramientas simplemente hay que ejecutar el siguiente comando en la terminal y con un entorno de python activado:

```bash
pip install black isort mypy pylint pre-commit
```

## Comportamiento del Pre-commit

**Pre-commit** es una herramienta que gestiona y ejecuta hooks antes de que los cambios en tu código sean confirmados (committed) en el repositorio. Su principal objetivo es automatizar tareas repetitivas de verificación y limpieza del código, asegurando que el código cumpla con ciertos estándares antes de ser añadido al historial del repositorio. A continuación, se explica cómo funciona el `pre-commit` y su configuración:

1. **Instalación de Hooks**: Al instalar `pre-commit` en un proyecto, los hooks definidos en el archivo `.pre-commit-config.yaml` son configurados para ejecutarse automáticamente antes de cada commit. Estos hooks pueden realizar diversas tareas, como formatear código, ordenar importaciones, verificar tipos, y mucho más.

2. **Ejecución Automática**: Cada vez que realizas un commit, `pre-commit` ejecuta los hooks en los archivos que has modificado. Si alguno de los hooks falla (por ejemplo, si `black` detecta que el código no está correctamente formateado), el commit es rechazado y se muestra un mensaje de error, indicando qué necesita ser corregido.

3. **Formateo y Limpieza del Código**: Hooks como `black` y `isort` formatean y ordenan automáticamente el código según las convenciones especificadas. Esto asegura que el código sea consistente en estilo y organización, lo cual es crucial para mantener la legibilidad y calidad del código.

4. **Verificación de Tipos y Estilo**: Herramientas como `mypy` y `pylint` se utilizan para verificar los tipos de datos y la adherencia a las convenciones de estilo de Python. `mypy` realiza verificaciones de tipo estáticas, mientras que `pylint` analiza el código en busca de errores y problemas de estilo.

5. **Configuración Sencilla y Extensible**: La configuración de `pre-commit` se realiza a través de un archivo `.pre-commit-config.yaml`, donde puedes definir los repositorios de hooks y las versiones específicas que deseas utilizar. Esto permite personalizar y extender fácilmente los checks que deseas ejecutar en tu código.

En el caso de que no deje realizar el commit, podrás ver que habrán archivos que se tengan que añadir de nuevo al `stagging area` mediante el comando `git add <file>` ya que pre-commit lo hará formateado correctamente según los hooks. En el caso de que no pasen de dicha fase, habrá que realizar ciertas modificaciones a mano para que cumplan con las condiciones especificadas en el fichero de configuración `.pre-commit-config.yaml`.