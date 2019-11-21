import collections
from dataclasses import dataclass, field
import logging
from pathlib import Path
import re
from typing import Dict

from lupa import LuaError, LuaRuntime

import factoratio.item as item

logger = logging.getLogger('factoratio')

@dataclass
class Prototypes():
  items: Dict[str, item.Item] = field(default_factory=dict)
  fluids: Dict[str, item.Fluid] = field(default_factory=dict)
  products: collections.ChainMap = field(init=False, repr=False)
  groups: Dict[str, item.ItemGroup] = field(default_factory=dict)
  subgroups: Dict[str, item.ItemGroup] = field(default_factory=dict)
  recipes: Dict[str, item.Recipe] = field(default_factory=dict)

  def __post_init__(self):
    self.products = collections.ChainMap(self.items, self.fluids)


class ProtoReader():
  """Internal class used to pull in prototype definitions from game data.

  Should not be used directly.
  """

  def __init__(self, path: Path):
    self.path = path
    self.lua = LuaRuntime()

    self.lua.execute(
      f"package.path = package.path .. ';{self.path.parent.as_posix()}/?.lua'")
    self.lua.execute('''data = {
      extend = function(self, otherdata)
        if type(otherdata) ~= 'table' or #otherdata == 0 then
          error('Invalid prototype array in ' .. python.eval('prototype'))
        end
        for key, block in pairs(otherdata) do
          table.insert(self, block)
        end
      end
    }''')

  def loadPrototypes(self, subdir: str) -> 'LuaTable':
    """Read and execute the prototype definitions in the given subdirectory.

    Populates the 'data' table within the Lua runtime, ready to be iterated.
    """
    self.lua.execute("data = {extend = data['extend']}")
    for prototype in self.path.glob(f'{subdir}/*.lua'):
      code = ''
      with prototype.open() as p:
        for line in p:
          # Some prototype definitions (e.g. 'gun.lua') contain a `require`
          # expression as a value. They typically call methods only available
          # during Factorio's runtime, so we just ignore them.
          if not re.search(r'= require\(', line):
            code += line
      try:
        self.lua.execute(code)
      except LuaError:
        logger.error(f"Lua error while executing '{prototype}'")
        raise

  def luaData(self):
    """Generate an iterator for the Lua 'data' table.

    Returns each child table; excludes the 'extend' method.
    """
    data = self.lua.globals().data
    tables = filter(lambda x: x[0] != 'extend', data.items())
    for table in (x[1] for x in tables):
      yield table


def initialize(protoPath: Path) -> Prototypes:
  """Load item, fluid, group, and recipe prototypes.

  Returns a Prototypes object with all relevant prototypes loaded from the
  definition files located at protoPath.

  Parameters
  ----------
  protoPath: Path
    The path to Factorio's 'prototypes' directory.
  """
  if not protoPath.exists():
    logger.critical(f"Could not find item prototypes at '{protoPath}'; "
      'cannot continue. Ensure that the path to the Factorio installation is '
      'correct and that it is properly installed.')

  result = Prototypes()
  items = result.items
  fluids = result.fluids
  products = result.products
  groups = result.groups
  subgroups = result.subgroups
  recipes = result.recipes

  reader = ProtoReader(protoPath)
  logger.info(f"Reading prototypes from '{protoPath}' ...")

  # TODO: Create Fuel objects
  # Get Item, Group, and Subgroup prototype definitions
  reader.loadPrototypes('item')
  for table in reader.luaData():
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

  # Get Fluid prototypes
  for prototype in protoPath.glob('fluid/*.lua'):
    with prototype.open() as p: code = p.read()
    try:
      reader.lua.execute(code)
    except LuaError:
      logger.error(f"Lua error while executing '{prototype}'")
      raise
  for table in reader.luaData():
    name = table.name
    if table.type != 'fluid': continue
    logger.debug(f"Adding Fluid '{name}'")
    fluids[name] = item.Fluid(name, table.default_temperature,
                              table.max_temperature, table.heat_capacity,
                              table.order)

  logger.info(f'Loaded {len(groups)} Groups, {len(subgroups)} Subgroups, '
              f'{len(items)} Items, and {len(fluids)} Fluids')

  # Get Recipe prototypes
  reader.loadPrototypes('recipe')
  for table in reader.luaData():
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
  return result