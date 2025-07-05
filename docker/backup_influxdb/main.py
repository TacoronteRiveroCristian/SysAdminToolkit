#!/usr/bin/env python3
"""
Orchestrator principal para el sistema de backup de InfluxDB
===========================================================

Este script es el punto de entrada principal del sistema de backup.
Carga todos los archivos .yaml de configuración del directorio /config
y ejecuta cada proceso de backup en paralelo.

Cada archivo .yaml representa un proceso de backup independiente que
puede mover datos entre diferentes servidores InfluxDB.
"""

import os
import sys
import signal
import argparse
import logging
from multiprocessing import Process, Queue, Event
from typing import List, Dict, Any
from datetime import datetime
import time

# Agregar el directorio src al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.backup_processor import BackupProcessor
from src.config_manager import ConfigManager, ConfigurationError


class BackupOrchestrator:
    """
    Orchestrator principal para el sistema de backup.

    Maneja la ejecución paralela de múltiples procesos de backup
    basados en archivos de configuración YAML.
    """

    def __init__(self, config_directory: str = '/config', verbose: bool = False):
        """
        Inicializa el orchestrator.

        Args:
            config_directory: Directorio con archivos de configuración
            verbose: Habilitar logging verbose
        """
        self.config_directory = config_directory
        self.verbose = verbose

        # Configurar logging básico
        self._setup_logging()

        # Estado del orchestrator
        self.processes: List[Process] = []
        self.results_queue = Queue()
        self.shutdown_event = Event()

        # Configurar manejo de señales
        self._setup_signal_handlers()

        self.logger = logging.getLogger('BackupOrchestrator')

    def _setup_logging(self) -> None:
        """Configura el logging básico del orchestrator."""
        level = logging.DEBUG if self.verbose else logging.INFO

        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def _setup_signal_handlers(self) -> None:
        """Configura los manejadores de señales."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating shutdown...")
            self.shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _find_config_files(self) -> List[str]:
        """
        Busca todos los archivos .yaml en el directorio de configuración.

        Returns:
            List[str]: Lista de rutas de archivos de configuración
        """
        config_files = []

        if not os.path.exists(self.config_directory):
            self.logger.error(f"Configuration directory not found: {self.config_directory}")
            return config_files

        for filename in os.listdir(self.config_directory):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                config_path = os.path.join(self.config_directory, filename)
                if os.path.isfile(config_path):
                    config_files.append(config_path)

        return sorted(config_files)

    def _validate_config_file(self, config_path: str) -> bool:
        """
        Valida un archivo de configuración.

        Args:
            config_path: Ruta del archivo de configuración

        Returns:
            bool: True si es válido
        """
        try:
            ConfigManager(config_path)
            return True
        except ConfigurationError as e:
            self.logger.error(f"Invalid configuration file {config_path}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error validating configuration file {config_path}: {e}")
            return False

    def _run_backup_process(self, config_path: str, results_queue: Queue,
                           shutdown_event: Event) -> None:
        """
        Ejecuta un proceso de backup individual.

        Args:
            config_path: Ruta del archivo de configuración
            results_queue: Cola para resultados
            shutdown_event: Evento de shutdown
        """
        process_name = os.path.basename(config_path)

        try:
            # Crear procesador de backup
            with BackupProcessor(config_path) as processor:
                # Verificar si debemos parar
                if shutdown_event.is_set():
                    results_queue.put({
                        'config': process_name,
                        'success': False,
                        'error': 'Shutdown requested',
                        'start_time': datetime.now().isoformat()
                    })
                    return

                # Ejecutar backup
                start_time = datetime.now()
                result = processor.run()
                end_time = datetime.now()

                # Preparar resultado
                result_data = {
                    'config': process_name,
                    'success': result.get('success', False),
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration': (end_time - start_time).total_seconds(),
                    'stats': result.get('stats', {})
                }

                if not result.get('success'):
                    result_data['error'] = result.get('error', 'Unknown error')

                results_queue.put(result_data)

        except Exception as e:
            results_queue.put({
                'config': process_name,
                'success': False,
                'error': str(e),
                'start_time': datetime.now().isoformat()
            })

    def _collect_results(self, expected_processes: int) -> List[Dict[str, Any]]:
        """
        Recolecta los resultados de los procesos.

        Args:
            expected_processes: Número esperado de procesos

        Returns:
            List[Dict]: Lista de resultados
        """
        results = []
        collected = 0

        while collected < expected_processes:
            try:
                # Esperar resultado con timeout
                result = self.results_queue.get(timeout=30)
                results.append(result)
                collected += 1

                config_name = result.get('config', 'Unknown')
                success = result.get('success', False)
                status = 'SUCCESS' if success else 'FAILED'

                self.logger.info(f"Process {config_name}: {status}")

                if not success:
                    error = result.get('error', 'Unknown error')
                    self.logger.error(f"Process {config_name} error: {error}")
                else:
                    stats = result.get('stats', {})
                    duration = result.get('duration', 0)
                    self.logger.info(f"Process {config_name} completed in {duration:.2f}s")

                    if stats:
                        records = stats.get('records_transferred', 0)
                        databases = stats.get('databases_processed', 0)
                        measurements = stats.get('measurements_processed', 0)
                        self.logger.info(f"  - Databases: {databases}, Measurements: {measurements}, Records: {records}")

            except Exception as e:
                self.logger.warning(f"Timeout waiting for process result: {e}")
                break

        return results

    def _print_summary(self, results: List[Dict[str, Any]]) -> None:
        """
        Imprime un resumen de los resultados.

        Args:
            results: Lista de resultados
        """
        if not results:
            self.logger.info("No results to summarize")
            return

        successful = sum(1 for r in results if r.get('success', False))
        failed = len(results) - successful

        self.logger.info("=" * 60)
        self.logger.info("BACKUP SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"Total processes: {len(results)}")
        self.logger.info(f"Successful: {successful}")
        self.logger.info(f"Failed: {failed}")

        # Estadísticas totales
        total_records = 0
        total_databases = 0
        total_measurements = 0

        for result in results:
            if result.get('success'):
                stats = result.get('stats', {})
                total_records += stats.get('records_transferred', 0)
                total_databases += stats.get('databases_processed', 0)
                total_measurements += stats.get('measurements_processed', 0)

        self.logger.info(f"Total records transferred: {total_records}")
        self.logger.info(f"Total databases processed: {total_databases}")
        self.logger.info(f"Total measurements processed: {total_measurements}")

        # Detalles de fallos
        if failed > 0:
            self.logger.info("\nFailed processes:")
            for result in results:
                if not result.get('success'):
                    config = result.get('config', 'Unknown')
                    error = result.get('error', 'Unknown error')
                    self.logger.error(f"  - {config}: {error}")

        self.logger.info("=" * 60)

    def run(self) -> int:
        """
        Ejecuta el orchestrator principal.

        Returns:
            int: Código de salida (0 = éxito, 1 = error)
        """
        start_time = datetime.now()

        self.logger.info("Starting InfluxDB Backup Orchestrator")
        self.logger.info(f"Configuration directory: {self.config_directory}")

        # Buscar archivos de configuración
        config_files = self._find_config_files()

        if not config_files:
            self.logger.error("No configuration files found")
            return 1

        self.logger.info(f"Found {len(config_files)} configuration files")

        # Validar archivos de configuración
        valid_configs = []
        for config_path in config_files:
            self.logger.info(f"Validating {os.path.basename(config_path)}...")
            if self._validate_config_file(config_path):
                valid_configs.append(config_path)
                self.logger.info(f"  ✓ Valid")
            else:
                self.logger.error(f"  ✗ Invalid")

        if not valid_configs:
            self.logger.error("No valid configuration files found")
            return 1

        self.logger.info(f"Starting {len(valid_configs)} backup processes...")

        # Iniciar procesos de backup
        for config_path in valid_configs:
            process_name = os.path.basename(config_path)

            process = Process(
                target=self._run_backup_process,
                args=(config_path, self.results_queue, self.shutdown_event),
                name=f"BackupProcess-{process_name}"
            )

            process.start()
            self.processes.append(process)

            self.logger.info(f"Started process for {process_name} (PID: {process.pid})")

        # Esperar resultados
        self.logger.info("Waiting for backup processes to complete...")

        try:
            results = self._collect_results(len(valid_configs))

            # Esperar a que todos los procesos terminen
            for process in self.processes:
                if process.is_alive():
                    process.join(timeout=60)
                    if process.is_alive():
                        self.logger.warning(f"Process {process.name} did not terminate, killing...")
                        process.terminate()
                        process.join(timeout=10)
                        if process.is_alive():
                            process.kill()

            # Mostrar resumen
            end_time = datetime.now()
            duration = end_time - start_time

            self.logger.info(f"All processes completed in {duration.total_seconds():.2f} seconds")
            self._print_summary(results)

            # Determinar código de salida
            failed_count = sum(1 for r in results if not r.get('success', False))
            return 1 if failed_count > 0 else 0

        except KeyboardInterrupt:
            self.logger.info("Received interrupt, shutting down...")
            self.shutdown_event.set()

            # Terminar procesos
            for process in self.processes:
                if process.is_alive():
                    process.terminate()

            # Esperar terminación
            for process in self.processes:
                process.join(timeout=10)
                if process.is_alive():
                    process.kill()

            return 130  # Código de salida para SIGINT

        except Exception as e:
            self.logger.error(f"Orchestrator error: {e}")
            return 1

    def cleanup(self) -> None:
        """Limpia recursos."""
        self.shutdown_event.set()

        # Terminar procesos activos
        for process in self.processes:
            if process.is_alive():
                process.terminate()

        # Esperar terminación
        for process in self.processes:
            process.join(timeout=5)
            if process.is_alive():
                process.kill()


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="InfluxDB Backup Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                           # Use default /config directory
  python main.py --config /path/to/config # Use custom config directory
  python main.py --verbose                # Enable verbose logging
  python main.py --validate-only          # Only validate configurations
        """
    )

    parser.add_argument(
        '--config', '-c',
        default='/config',
        help='Configuration directory (default: /config)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate configuration files, do not run backups'
    )

    args = parser.parse_args()

    # Crear orchestrator
    orchestrator = BackupOrchestrator(
        config_directory=args.config,
        verbose=args.verbose
    )

    try:
        if args.validate_only:
            # Solo validar configuraciones
            config_files = orchestrator._find_config_files()

            if not config_files:
                print("No configuration files found")
                return 1

            print(f"Validating {len(config_files)} configuration files...")

            valid_count = 0
            for config_path in config_files:
                filename = os.path.basename(config_path)
                if orchestrator._validate_config_file(config_path):
                    print(f"  ✓ {filename}")
                    valid_count += 1
                else:
                    print(f"  ✗ {filename}")

            print(f"\nValidation complete: {valid_count}/{len(config_files)} valid")
            return 0 if valid_count == len(config_files) else 1

        else:
            # Ejecutar backups
            exit_code = orchestrator.run()
            return exit_code

    except Exception as e:
        print(f"Fatal error: {e}")
        return 1

    finally:
        orchestrator.cleanup()


if __name__ == '__main__':
    exit(main())
