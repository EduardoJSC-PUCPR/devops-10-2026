"""Configuração de logs da aplicação."""

import logging
from datetime import datetime, timedelta, timezone
from time import struct_time

FUSO_HORARIO = timezone(timedelta(hours=-3))


def converter_horario(timestamp: float) -> struct_time:
    """Converte um timestamp para o fuso horário UTC-3."""
    return datetime.fromtimestamp(timestamp, FUSO_HORARIO).timetuple()


LOGGER = logging.getLogger("devops")
LOGGER.setLevel(logging.DEBUG)
LOGGER.propagate = False

if not LOGGER.handlers:
    saida_padrao = logging.StreamHandler()
    arquivo = logging.FileHandler("aplicacao.log", encoding="utf-8")

    formatador = logging.Formatter(
        "%(name)s | %(levelname)s | %(asctime)s | "
        "%(filename)s:%(lineno)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S -03:00",
    )
    formatador.converter = converter_horario

    saida_padrao.setFormatter(formatador)
    arquivo.setFormatter(formatador)

    LOGGER.addHandler(saida_padrao)
    LOGGER.addHandler(arquivo)
