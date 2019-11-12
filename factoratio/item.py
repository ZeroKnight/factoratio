from collections import abc
from typing import List, Union

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
    return (f'{self.__class__.__name__}({self.name}, {self.order}, '
            f'{self.parent}): {self._children!r})')

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


class Item():
  """Class representing an arbitrary game item."""

  def __init__(self, name: str, type_: str, subgroup: ItemGroup, order: str):
    self.name = name
    self.type = type_
    self.subgroup = subgroup
    self.order = order
    # self.icon = ... # TODO: Will be relevent when the GUI code is started


class Ingredient():
  """Class representing a crafting ingredient.

  An Ingredient is a specific item in some quantity; typically used in the
  creation of a Recipe.

  Attributes
  ----------
  item: Item
      The item to be used as an ingredient.

  count: int
      The amount of the item for this ingredient.
  """

  # TODO: Create Item class and add string lookup
  def __init__(self, item: Union[Item, str], count: int):
    self.item = item
    self.count = count

  def __repr__(self):
    return f'{self.__class__.__name__}({self.item!r}, {self.count!r})'

  def __str__(self):
    return f'{self.count}x {self.item.name}'


class Recipe():
  """Base class for a crafting recipe.

  A Recipe contains a set of input and output Ingredients and a crafting time.

  Attributes
  ----------
  time: float
      The time for the recipe to complete. Modified by a producer's crafting
      speed.

  input_, output: List of Ingredients
      List of Ingredients for recipe input and output.
  """

  def __init__(self, time: float, input_: List[Ingredient],
               output: List[Ingredient]):
    self.time = time
    self.input = input_
    self.output = output

  def __repr__(self):
    return (f'{self.__class__.__name__}({self.time!r}, {self.input!r}, '
            f'{self.output!r})')

  @classmethod
  def miningRecipe(cls, time: float, item: Item, input_: List[Ingredient]=None,
                   output: List[Ingredient]=None):
    """Alternative constructor for mining drill recipes.

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
        The item that this drill extracts as output by default.

    input_: List of Ingredients, optional
        Any ingredients the drill requires to mine the resource. Defaults to
        an empty list.

    output: List of Ingredients, optional
        The products that the drill extracts. Defaults to the item parameter
        with a quantity of one.
    """
    if input_ is None:
      input_ = []
    if output is None:
      output = [Ingredient(item, 1)]
    return cls(time, input_, output)

  def getInputByName(self, name: str) -> Ingredient:
    """Get an input ingredient by its name.

    Returns None if the item could not be found by the given name.
    """
    for ingredient in self.input:
      if ingredient.item.name == name:
        return ingredient
    return None

  def getOutputByName(self, name: str) -> Ingredient:
    """Get an output ingredient by its name.

    Returns None if the item could not be found by the given name.
    """
    for ingredient in self.output:
      if ingredient.item.name == name:
        return ingredient
    return None