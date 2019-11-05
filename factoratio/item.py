from typing import List, Union

class Item():
  """Class representing an arbitrary game item.

  Item groups are shown above the list of craftable items in the player's
  inventory, e.g. Logistics, Production, Intermediates, Combat, etc.

  Item subgroups are more fine-grained categories for items, e.g. "ammo",
  "storage", "belt", etc.
  """

  def __init__(self, name: str, type_: str, group: str, subgroup: str,
               order: str):
    self.name = name
    self.type = type_
    self.group = group
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