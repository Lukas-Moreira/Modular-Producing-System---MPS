# utils.py
import logging
from pathlib import Path

class CustomFormatter(logging.Formatter):
    """Formatador personalizado para logs com tratamento de encoding"""
    def format(self, record):
        msg = super().format(record)
        try:
            return msg.encode('utf-8').decode('utf-8')
        except UnicodeError:
            return msg.encode('ascii', errors='ignore').decode('ascii')

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configura sistema de logging
    
    Args:
        log_level: Nível de log (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger('FactoryIO')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove handlers existentes para evitar duplicação
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    try:
        # Cria diretório de logs
        log_path = Path("logs")
        log_path.mkdir(exist_ok=True)
        
        # Handler para arquivo
        file_handler = logging.FileHandler(
            log_path / 'factory_io_scanner.log', 
            encoding='utf-8'
        )
        file_formatter = CustomFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Handler para console (apenas erros)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_formatter = CustomFormatter('%(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
    except Exception as e:
        print(f"⚠️ Erro configurando logging: {e}")
    
    return logger
