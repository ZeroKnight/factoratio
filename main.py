import configparser
import logging
from pathlib import Path
import re
import sys

from lupa import LuaError, LuaRuntime

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
  protoPath = factorioPath / 'data' / 'base' / 'prototypes'
  if not protoPath.exists():
    logger.critical(f"Could not find item prototypes at '{protoPath}'; "
      'cannot continue. Ensure that the path to the Factorio installation is '
      'correct and that it is properly installed.')

  items = {}
  lua = LuaRuntime()
  lua.execute(
    f"package.path = package.path .. ';{protoPath.parent.as_posix()}/?.lua'")
  lua.execute('''data = {
    extend = function(self, otherdata)
      if type(otherdata) ~= 'table' or #otherdata == 0 then
        error('Invalid prototype array in ' .. python.eval('prototype'))
      end
      for _, block in ipairs(otherdata) do
        table.insert(self, block)
      end
    end
  }''')
  for prototype in protoPath.glob('item/*.lua'):
    code = ''
    with prototype.open() as p:
      for line in p:
        # The 'gun.lua' prototype has a require that utilizes a 'util' function
        # that's probably only used during Factorio's data runtime. We
        # obviously don't have the definition, but also don't need it anyway,
        # so skip it.
        if not re.search(r'= require\(', line):
          code += line
    try:
      lua.execute(code)
    except LuaError:
      logger.error(f"Lua error while executing '{prototype}'")
      raise

  tables = filter(lambda x: x[0] != 'extend', lua.globals().data.items())
  for table in (x[1] for x in tables):
    if table.flags and 'hidden' in table.flags.values():
      logger.debug(f'Skipping hidden item {table.name} in {prototype.name}')
      continue
    name = table['name']
    items[name] = dict(filter(
      lambda x: re.match(r'(?:sub)?group|order|type', x[0]), table.items()))

  pass