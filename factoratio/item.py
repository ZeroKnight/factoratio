from collections import abc
from dataclasses import dataclass
from typing import List, Union

from factoratio.util import Joule

class ItemGroup(abc.MutableMapping):
  """Class representing an item group used to categorize items.

  ItemGroups are mappings of group names to either a subordinate ItemGroup or
  to an Item. In the former case, the ItemGroup's parent is None and is
  interpreted as a top-level group. In the latter case, the ItemGroup is
  interpreted as a "subgroup" of a top-level ItemGroup that can be referenced
  by its parent attribute.

  In game, top-level item groups are shown above the list of craftable items
  in the player's inventory, e.g. Logistics, Production, Intermediates,
  Combat, etc.

  Item subgroups are more fine-grained categories for items, e.g. "ammo",
  "storage", "belt", etc, and belong to a top-level group.

  Attributes
  ----------
  name: str
      The name of the item group, e.g. 'Logistics'.

  order: str
      A string defining the sort order for this group.

  parent: ItemGroup, optional
      A reference to this item group's parent if it's a subgroup, or None if
      it's a top-level group, which is the default.

  Parameters
  ----------
  *args, **kwargs:
      Any extra parameters will be used to populate the ItemGroup mapping.
  """

  def __init__(self, name: str, order: str, parent: 'ItemGroup'=None,
               *args, **kwargs):
    self.name = name
    self.order = order
    self.parent = parent
    self._children = {}
    for k, v in zip(args[::2], args[1::2]): self[k] = v
    for k, v in kwargs.items(): self[k] = v

  def __repr__(self):
    return (f'{self.__class__.__name__}({self.name!r}, {self.order!r}, '
            f'{self.parent!r})')

  def __str__(self):
    return self.name

  def __setitem__(self, key: str, value):
    if isinstance(key, str):
      if isinstance(value, (self.__class__, Item)):
        self._children[key] = value
      else:
        raise TypeError(f'{self.__class__.__name__} values must be of type '
                        f'{self.__class__.__name__} or Item')
    else:
      raise TypeError(f'{self.__class__.__name__} keys must be of type str')

  def __getitem__(self, key: str):
    return self._children[key]

  def __delitem__(self, key):
    del self._children[key]

  # TODO: return based on children objects' order member
  def __iter__(self):
    return iter(self._children)

  def __len__(self):
    return len(self._children)

  def __bool__(self):
    return self._children.__bool__()


@dataclass
class Item():
  """Class representing an arbitrary game item.

  Attributes
  ----------
  name: str
      The name of the Item as defined by its prototype; not to be confused
      with a localized name.

  type: str
      The Item's type as defined by its prototype.

  subgroup: ItemGroup
      The Subgroup that this Item belongs to.

  order: str
      A string defining the sort order for this Item.
  """

  name: str
  type: str
  subgroup: ItemGroup
  order: str
  # icon = ... # TODO: Will be relevent when the GUI code is started

  def __str__(self):
    return f'{self.name}'


@dataclass
class Fluid():
  """Class representing an arbitrary game fluid.

  Attributes
  ----------
  name: str
      The name of the Fluid as defined by its prototype; not to be confused
      with a localized name.

  temp_default: float
      The default and also minimum temperature of this Fluid

  temp_max: float
      The maxmimum temperature of this Fluid

  heat_capacity: Joule
      The amount of Joules needed to heat 1 unit of this Fluid by 1C

  order: str
      A string defining the sort order for this Fluid.
  """

  name: str
  temp_default: float
  temp_max: float
  heat_capacity: Union[Joule, str]
  order: str
  # icon: ... # TODO

  def __post_init__(self):
    if isinstance(self.heat_capacity, str):
      self.heat_capacity = Joule(self.heat_capacity)
    else:
      raise TypeError('heat_capacity must be of type str or Joule')

  def __str__(self):
    return f'{self.name}'


@dataclass
class Ingredient():
  """Class representing a crafting ingredient.

  An Ingredient is a specific Item or Fluid in some quantity for use in a
  Recipe.

  Attributes
  ----------
  what: Item or Fluid
      The Item or Fluid to be used as an Ingredient.

  count: int
      The amount of the Item or Fluid for this Ingredient. Defaults to 1.

  probability: float
      The chance that this Ingredient is returned in a Recipe's output.
      Expressed as a decimal percentage. Defaults to 1.
  """

  what: Union[Item, Fluid]
  count: int = None
  probability: float = None

  def __post_init__(self):
    if not isinstance(self.what, (Item, Fluid)):
      raise TypeError("'what' member must be of type Item or Fluid")
    if self.count is None: self.count = 1
    if self.probability is None: self.probability = 1

  def __str__(self):
    return f'{self.count}x {self.item.name}'


class Recipe():
  """Base class for a crafting recipe.

  A Recipe contains a set of input and output Ingredients and a crafting time.

  Attributes
  ----------
  input_, output: List of Ingredients
      List of Ingredients for recipe input and output.

  time: float
      The time for the recipe to complete. Modified by a Producer's crafting
      speed.

  input_, output: List of Ingredients
      List of Ingredients for Recipe input and output.
  """

  def __init__(self, time: float, input_: List[Ingredient],
               output: List[Ingredient]):
    self.time = time
    self.input = input_
    self.output = output
    self._expensive = None
    self._isExpensive = False

  def __repr__(self):
    return (f'{self.__class__.__name__}({self.time!r}, {self.input!r}, '
            f'{self.output!r})')

  @classmethod
  def miningRecipe(cls, time: float, item: Item, input_: List[Ingredient]=None,
                   output: List[Ingredient]=None):
    """Alternative constructor for mining drill Recipes.

    Typically a mining drill produces whatever resource it is placed on, and
    in vanilla Factorio, only uranium ore has an input requirement. Thus,
    this is a convenience constructor that takes care of the input and output
    by default.

    Parameters
    ----------
    time: float
        The time for the recipe to complete. Modified by the drill's mining
        speed.

    item: Item
        The Item that this drill extracts as output by default.

    input_: List of Ingredients, optional
        Any Ingredients the drill requires to mine the resource. Defaults to
        an empty list.

    output: List of Ingredients, optional
        The products that the drill extracts. Defaults to the item parameter
        with a quantity of one.
    """
    if input_ is None:
      input_ = []
    if output is None:
      output = [Ingredient(item, 1)]
    return cls(input_, output, time)

  def expensive(self) -> 'Recipe':
    """Returns the Expensive Mode variant of this Recipe."""
    return self._expensive

  def isExpensive(self) -> bool:
    """Whether or not this Recipe is an Expensive Mode variant."""
    return self._isExpensive

  def addExpensiveMode(self, recipe: 'Recipe'):
    """Adds the Expensive Mode variant of this Recipe to the current Recipe.

    Parameters
    ----------
    recipe: Recipe
        The expensive variant Recipe to add.
    """
    if isinstance(recipe, self.__class__):
      self._expensive = recipe
      recipe._isExpensive = True
    else:
      raise TypeError(f'Argument must be of type {self.__class__.__name__}')

  def getInputByName(self, name: str) -> Ingredient:
    """Get an input Ingredient by its name.

    Returns None if the Item could not be found by the given name.
    """
    for ingredient in self.input:
      if ingredient.what.name == name:
        return ingredient
    return None

  def getOutputByName(self, name: str) -> Ingredient:
    """Get an output ingredient by its name.

    Returns None if the item could not be found by the given name.
    """
    for ingredient in self.output:
      if ingredient.what.name == name:
        return ingredient
    return None