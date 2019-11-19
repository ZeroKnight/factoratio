import collections
import configparser
import logging
from pathlib import Path
import re
import sys

from lupa import LuaError, LuaRuntime

from factoratio import APPNAME
import factoratio.fuel as fuel
import factoratio.producer as producer
import factoratio.item as item
import factoratio.util as util
from factoratio.util import Joule, Watt

logger = logging.getLogger('factoratio')

items, fluids, groups, subgroups, recipes = ({} for _ in range(5))
products = collections.ChainMap(items, fluids)

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

def luaDataIter(data: 'LuaTable'):
  """Generate an iterator for the Lua 'data' table.

  Returns each child table; excludes the 'extend' method.
  """
  tables = filter(lambda x: x[0] != 'extend', data.items())
  for table in (x[1] for x in tables):
    yield table

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
  if not protoPath.exists():
    logger.critical(f"Could not find item prototypes at '{protoPath}'; "
      'cannot continue. Ensure that the path to the Factorio installation is '
      'correct and that it is properly installed.')

  lua = LuaRuntime()
  lua.execute(
    f"package.path = package.path .. ';{protoPath.parent.as_posix()}/?.lua'")
  lua.execute('''data = {
    extend = function(self, otherdata)
      if type(otherdata) ~= 'table' or #otherdata == 0 then
        error('Invalid prototype array in ' .. python.eval('prototype'))
      end
      for key, block in pairs(otherdata) do
        table.insert(self, block)
      end
    end
  }''')

  # Get Item, Group, and Subgroup prototype definitions
  logger.info(f"Reading prototypes from '{protoPath}' ...")
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
  for table in luaDataIter(lua.globals().data):
    if table.flags and 'hidden' in table.flags.values():
      logger.debug(f"Skipping hidden Item '{table.name}'")
      continue
    name = table.name
    type_ = table.type
    if type_ == 'item-group':
      logger.debug(f"Adding Group '{name}'")
      groups[name] = item.ItemGroup(name, table.order)
    # Defer creating the actual objects until after all (Sub)Groups are known
    elif type_ == 'item-subgroup':
      logger.debug(f"Adding Subgroup '{name}'")
      subgroups[name] = {'order': table.order, 'parent': table.group}
    else:
      logger.debug(f"Adding Item '{name}'")
      items[name] = {'type_': type_, 'parent': table.subgroup,
                     'order': table.order}

  # Link the Groups, Subgroups, and Items together
  for k, v in subgroups.items():
    subgroups[k] = item.ItemGroup(k, v['order'], groups[v['parent']])
    groups[v['parent']][k] = subgroups[k]
  for k, v in items.items():
    items[k] = item.Item(k, v['type_'], subgroups[v['parent']], v['order'])
    subgroups[v['parent']][k] = items[k]

  # Remove Subgroups with no Items; i.e. all its Items were "hidden"
  hidden_subgroups = []
  for k, v in subgroups.items():
    if not len(v):
      hidden_subgroups.append(k)
      del groups[v.parent.name][v.name]
  for subgroup in hidden_subgroups:
    del subgroups[subgroup]

  logger.info(f'Loaded {len(groups)} Groups, {len(subgroups)} Subgroups, and '
              f'{len(items)} Items')

  # Get Fluid prototypes
  lua.execute("data = {extend = data['extend']}")
  for prototype in protoPath.glob('fluid/*.lua'):
    with prototype.open() as p: code = p.read()
    try:
      lua.execute(code)
    except LuaError:
      logger.error(f"Lua error while executing '{prototype}'")
      raise
  for table in luaDataIter(lua.globals().data):
    name = table.name
    if table.type != 'fluid': continue
    fluids[name] = item.Fluid(name, table.default_temperature,
                              table.max_temperature, table.heat_capacity,
                              table.order)

  # Get Recipe prototypes
  lua.execute("data = {extend = data['extend']}")
  for prototype in protoPath.glob('recipe/*.lua'):
    with prototype.open() as p: code = p.read()
    try:
      lua.execute(code)
    except LuaError:
      logger.error(f"Lua error while executing '{prototype}'")
      raise
  for table in luaDataIter(lua.globals().data):
    # Skip recipes for hidden items
    if table.name not in items or table.type != 'recipe': continue
    name = table.name
    # TODO: Handle expensive mode recipes. Store two Ingredient sets in Recipe.
    ingTable = (table.normal or table.expensive or table)['ingredients']
    input_ = [
      item.Ingredient(products[x[1] or x.name], x[2] or x.amount)
      for x in ingTable.values()
    ]
    if 'result' in table:
      output = [item.Ingredient(products[table.result], table.result_count)]
    elif 'results' in table:
      output = [
        item.Ingredient(products[x.name], x.amount, x.probability)
        for x in table.results.values()
      ]
    recipes[name] = item.Recipe(input_, output, table.energy_required)

  logger.info(f'Loaded {len(recipes)} Recipes')

  pass
