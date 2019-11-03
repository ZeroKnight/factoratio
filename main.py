import configparser
import logging
from pathlib import Path
import sys

from lupa import LuaRuntime

from factoratio import APPNAME
import factoratio.fuel as f
import factoratio.producer as p
import factoratio.recipe as r
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

  items = {}
  lua = LuaRuntime()
  protoPath = factorioPath / 'data' / 'base' / 'prototypes'
  if not protoPath.exists():
    logger.critical(f"Could not find item prototypes at '{protoPath}'; "
      'cannot continue. Ensure that the path to the Factorio installation is '
      'correct and that it is properly installed.')
  for prototype in protoPath.glob('item/*.lua'):
    data = ''
    with prototype.open() as p:
      while p.readline().strip() != 'data:extend(': pass
      for line in p:
        data += line.strip()
      if data[-1] == ')': data = data[:-1]
    for table in lua.eval(data).values():
      # FIXME: crashes when parsing demo-crash-site-item.lua because there's two
      # data:extend calls. Might be a better idea to use lua.execute to create
      # our own data:extend that does or facilitatse the same as below
      name = table['name']
      items[name] = dict(filter(lambda x: x[0] != 'name', table.items()))

  pass