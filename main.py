import configparser
import logging
from pathlib import Path
import re
import sys

from factoratio import APPNAME
import factoratio.fuel as fuel
import factoratio.item as item
import factoratio.producer as producer
import factoratio.prototype as prototype
import factoratio.util as util
from factoratio.util import Joule, Watt

logger = logging.getLogger('factoratio')

def readConfig(cfg: Path) -> configparser.ConfigParser:
  """Load Factoratio's user configuration from the given path.

  Parameters
  ----------
  cfg: Path
      The path to the configuration file.

  Returns a ConfigParser object.
  """
  if not cfg.exists():
    logger.info(f"Configuration file not found at '{cfg}'")
  config = configparser.ConfigParser()
  config.read(cfg)
  return config

if __name__ == "__main__":
  configDir = util.getConfigPath()
  if not configDir.exists(): configDir.mkdir()

  # Set up logging
  # TODO: formatting
  logger.setLevel(logging.DEBUG) # TEMP
  logger.addHandler(logging.StreamHandler())
  logPath = util.getConfigPath(Path(f'{APPNAME}.log'))
  logger.addHandler(logging.FileHandler(logPath))

  # TODO: check for --config option. use argparse
  configPath = util.getConfigPath(f'{APPNAME}.ini')
  config = readConfig(configPath)
  factorioPath = config.get(APPNAME, 'gamedir',
                            fallback=util.getFactorioPath())
  if factorioPath is None:
    logger.error('Could not determine Factorio install location.')
    factorioPath = Path(input('Enter path to Factorio installation: '))
  protoPath = factorioPath / 'data' / 'base' / 'prototypes'
  prototypes = prototype.initialize(protoPath)

  pass
