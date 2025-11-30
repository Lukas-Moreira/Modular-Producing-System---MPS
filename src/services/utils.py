# utils.py
import logging
from pathlib import Path


class CustomFormatter(logging.Formatter):
    """Formatador personalizado para logs com tratamento de encoding"""

    def format(self, record):
        msg = super().format(record)
        try:
            return msg.encode("utf-8").decode("utf-8")
        except UnicodeError:
            return msg.encode("ascii", errors="ignore").decode("ascii")


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configura sistema de logging

    Args:
        log_level: Nível de log (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Logger configurado
    """
    logger = logging.getLogger("MPS Factory")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Garante que o diretório de logs exista antes de configurar handlers
    log_path = Path("logs")
    try:
        log_path.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Se não for possível criar o diretório, continuamos e deixamos
        # o basicConfig/handlers lidarem com possíveis erros mais abaixo.
        pass

    logging.basicConfig(
        filename=log_path / "Modular_Producing_System.log",  # Nome do arquivo de log
        filemode="w",  # Sobrescreve o arquivo a cada execução
        level=getattr(
            logging, log_level.upper()
        ),  # Nível mínimo de mensagens a registrar
        format="%(asctime)s - %(name)s -  %(levelname)s - %(message)s",  # Formato do log
        encoding="utf-8",  # Encoding do arquivo de log
    )

    # Configuramos handlers manualmente para evitar que logging.basicConfig
    # tente abrir o arquivo antes do diretório existir ou cause duplicação.
    # Definimos nível no logger explicitamente acima.

    # Remove handlers existentes para evitar duplicação
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    try:
        # Handler para arquivo
        file_handler = logging.FileHandler(
            log_path / "Modular_Producing_System.log", encoding="utf-8"
        )
        file_formatter = CustomFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Handler para console (mostrar INFO no terminal para facilitar debug)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = CustomFormatter("%(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    except Exception as e:
        print(f"⚠️ Erro configurando logging: {e}")

    return logger
