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

class LoggerManager:
    """ Gerenciador de logging para a aplicação MPS Festo. """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LoggerManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance
    
    def __init__(self, log_level: str = "INFO"):
        self.logger = logging.getLogger('MPS_Festo')
        self.logger.setLevel(getattr(logging, log_level.upper()))

        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

        try:
            log_path = Path("logs")
            log_path.mkdir(exist_ok=True)

            file_handler = logging.FileHandler(
                log_path / 'mps_festo_scanner.log',
                encoding='utf-8'
            )
            file_formatter = CustomFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.ERROR)
            console_formatter = CustomFormatter('%(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

        except Exception as e:
            print(f"⚠️ Erro configurando logging: {e}")

    def set_name(self, name: str):
        """ Define o nome do logger. """
        self.logger.name = name
    
    def set_level(self, log_level: str):
        """ Define o nível de logging. """
        self.logger.setLevel(getattr(logging, log_level.upper()))

loggerManager = LoggerManager()  # Instância singleton do LoggerManager