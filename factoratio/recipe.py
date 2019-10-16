from typing import Set, Union

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


# TBD: List or Set for Ingredients?
class Recipe():
  """Base class for a crafting recipe.

  A Recipe contains a set of input and output Ingredients and a crafting time.

  Attributes
  ----------
  time: float
      The time for the recipe to complete. Modified by a producer's crafting
      speed.

  input_, output: Set of Ingredients
      Set of Ingredients for recipe input and output.
  """

  def __init__(self, time: float, input_: Set[Ingredient],
               output: Set[Ingredient]):
    self.time = time
    self.input = input_
    self.output = output

  def __repr__(self):
    return (f'{self.__class__.__name__}({self.time!r}, {self.input!r}, '
            f'{self.output!r})')

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