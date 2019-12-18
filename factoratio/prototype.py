import collections
from dataclasses import dataclass, field
import functools
import logging
from pathlib import Path
import re
from typing import Dict

from lupa import LuaError, LuaRuntime

from factoratio.fuel import Fuel
import factoratio.item as item

logger = logging.getLogger('factoratio')

@dataclass
class Prototypes():
  items: Dict[str, item.Item] = field(default_factory=dict)
  fluids: Dict[str, item.Fluid] = field(default_factory=dict)
  fuels: Dict[str, Fuel] = field(default_factory=dict)
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

  def __init__(self, path: Path, prototypes: Prototypes):
    self.path = path
    self.lua = LuaRuntime()
    self.prototypes = prototypes

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

  def _make(type_):
    """Internal decorator for implementing make* methods."""
    def decorator__make(func):
      @functools.wraps(func)
      def wrapper__make(self, table, *args, **kwargs):
        if type_ is None or type_ == table.type:
          obj = func(self, table, *args, **kwargs)
          return obj
        else:
          raise ValueError(f"Table type must be '{type_}'; got '{table.type}'")
      return wrapper__make
    return decorator__make

  @_make('item-group')
  def makeGroup(self, table: 'LuaTable') -> item.ItemGroup:
    """Create an ItemGroup object from a group prototype definition.

    Parameters
    ----------
    table: LuaTable
        A table containing a group prototype definition.
    """
    if table.name in self.prototypes.groups:
      group = self.prototypes.groups[table.name]
      # Fill in 'order' attribute that was deferred in makeSubGroup
      group.order = table.order
    else:
      group = item.ItemGroup(table.name, table.order)
    return group

  @_make('item-subgroup')
  def makeSubGroup(self, table: 'LuaTable') -> item.ItemGroup:
    """Create an ItemGroup object from a subgroup prototype definition.

    Parameters
    ----------
    table: LuaTable
        A table containing a subgroup prototype definition.
    """
    if table.group in self.prototypes.groups:
      parent = self.prototypes.groups[table.group]
    else:
      # Defer setting 'order' until this group is found later
      parent = item.ItemGroup(table.group, None)
      self.prototypes.groups[parent.name] = parent

    if table.name in self.prototypes.subgroups:
      subgroup = self.prototypes.subgroups[table.name]
      # Fill in 'parent' and 'order' that was deferred in makeItem
      subgroup.parent = parent
      subgroup.order = table.order
    else:
      subgroup = item.ItemGroup(table.name, table.order, parent)
    parent[subgroup.name] = subgroup
    return subgroup

  @_make(None)
  def makeItem(self, table: 'LuaTable') -> item.Item:
    """Create an Item object from an item prototype definition.

    Parameters
    ----------
    table: LuaTable
        A table containing an item prototype definition.
    """
    if table.subgroup in self.prototypes.subgroups:
      subgroup = self.prototypes.subgroups[table.subgroup]
    else:
      # Defer setting 'parent' and 'order' until this subgroup is found later
      subgroup = item.ItemGroup(table.subgroup, None, None)
      self.prototypes.subgroups[subgroup.name] = subgroup
    newItem = item.Item(table.name, table.type, subgroup, table.order)
    subgroup[newItem.name] = newItem
    return newItem

  @_make('fluid')
  def makeFluid(self, table: 'LuaTable') -> item.Fluid:
    """Create a Fluid object from a fluid prototype definition.

    Parameters
    ----------
    table: LuaTable
        A table containing a fluid prototype definition.
    """
    return item.Fluid(
      table.name, table.default_temperature, table.max_temperature,
      table.heat_capacity, table.order
    )

  @_make(None)
  def makeFuel(self, table: 'LuaTable') -> Fuel:
    """Create a Fuel object from an item prototype definition.

    Parameters
    ----------
    table: LuaTable
        A table containing an item prototype definition with fuel attributes.
    """
    return Fuel(table.name, table.fuel_value)

  @_make('recipe')
  def makeRecipe(self, table: 'LuaTable', expensive: bool=False) -> item.Recipe:
    """Create a Recipe object from a recipe prototype definition.

    Parameters
    ----------
    table: LuaTable
        A table containing a recipe prototype definition.

    expensive: bool, optional
        Whether or not the expensive variant should be used to create the
        Recipe. Defaults to False.
    """
    name = table.name
    table = table.expensive if expensive else (table.normal or table)
    products = self.prototypes.products
    input_ = [
      item.Ingredient(products[x[1] or x.name], x[2] or x.amount)
      for x in table.ingredients.values()
    ]
    if 'result' in table:
      output = [item.Ingredient(products[table.result], table.result_count)]
    elif 'results' in table:
      output = [
        item.Ingredient(products[x.name], x.amount, x.probability)
        for x in table.results.values()
      ]
    return item.Recipe(input_, output, table.energy_required)


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
  fuels = result.fuels
  products = result.products
  groups = result.groups
  subgroups = result.subgroups
  recipes = result.recipes

  reader = ProtoReader(protoPath, result)
  logger.info(f"Reading prototypes from '{protoPath}' ...")

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
      groups[name] = reader.makeGroup(table)
    elif type_ == 'item-subgroup':
      logger.debug(f"Adding Subgroup '{name}'")
      subgroups[name] = reader.makeSubGroup(table)
    else:
      logger.debug(f"Adding Item '{name}'")
      items[name] = reader.makeItem(table)
      if table.fuel_value:
        fuels[name] = reader.makeFuel(table)

  # Remove Groups and Subgroups that ended up being empty due to hidden Items
  for name, subgroup in dict(subgroups).items():
    if not len(subgroup):
      logger.debug(f"Removing empty Subgroup '{subgroup}'")
      del groups[subgroup.parent.name][subgroup.name]
      del subgroups[subgroup.name]
  for name, group in dict(groups).items():
    if not len(group):
      logger.debug(f"Removing empty Group '{group}'")
      del groups[name]

  # Get Fluid prototypes
  reader.loadPrototypes('fluid')
  for table in reader.luaData():
    logger.debug(f"Adding Fluid '{table.name}'")
    fluids[table.name] = reader.makeFluid(table)

  logger.info(f'Loaded {len(groups)} Groups, {len(subgroups)} Subgroups, '
              f'{len(items)} Items, and {len(fluids)} Fluids')

  # Get Recipe prototypes
  nExp = 0
  reader.loadPrototypes('recipe')
  for table in reader.luaData():
    # Skip recipes for hidden items
    if table.name not in items: continue
    recipe = reader.makeRecipe(table, expensive=False)
    if table.expensive:
      recipe.addExpensiveMode(reader.makeRecipe(table, expensive=True))
      nExp += 1
    recipes[table.name] = recipe

  logger.info(f'Loaded {len(recipes)} normal and {nExp} expensive Recipes')
  return result
