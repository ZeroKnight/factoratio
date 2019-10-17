from factoratio.fuel import Burner, Fuel
from factoratio.recipe import Ingredient, Recipe
from factoratio.util import Watt

class Module():
  """A module for a producer.

  Modifies various aspects of the producer's operation including energy
  consumption, operation speed, productivity bonus, and pollution output.

  All modifiers are a positive or negative percentage expressed as a
  real number, e.g. +30% -> 0.30, -15% -> -0.15.

  Attributes
  ----------
  name : str
      The name of the module. Can be anything, but is typically the in-game
      name.

  tier : int
      A positive, non-zero integer representing the module tier. Plain old data
      not used in any calculations.

  energy: float
      The energy multiplier for this module. Affects energy consumption rate.

  speed: float
      The speed multiplier for this module. Affects production speed.

  productivity: float
      The productivity multiplier for this module. Currently only ever
      positive in Factorio. Determines amount of extra free products.

  pollution: float
      The pollution multiplier for this module. Affects amount of pollution
      produced.
  """

  def __init__(self, name: str, tier: int, energy: float, speed: float,
               productivity: float, pollution: float):
    self.name = name
    self.tier = tier
    self.energy = energy
    self.speed = speed
    self.productivity = productivity
    self.pollution = pollution

  def __repr__(self):
    return f'{__class__.__name__}({self.name!r}, {self.tier!r}, ' \
           f'{self.energy!r}, {self.speed!r}, {self.productivity!r}, ' \
           f'{self.pollution!r})'

  def __str__(self):
      return f'Tier {self.tier} {self.name} Module'


# TODO: Include productivity bonus in relevent methods
class Producer():
  """Base class for entities that produce an item as output.

  Attributes
  ----------
  name: str
      The name of this producer. Can be anything, but is typically the
      in-game name.

  craftSpeed: float
      The speed at which this producer crafts a given recipe; the recipe
      crafting time is divided by this speed to yield the total crafting
      time.

  maxSlots: int
      The total number of module slots this producer supports.

  energyUsage: factoratio.util.Watt
      The amount of energy consumed by this producer per second while
      actively working, i.e. for the duration of a crafting cycle.

  drain: factoratio.util.Watt
      The amount of energy constantly consumed by this producer, just by
      being connected to the power grid.

  pollution: int
      The amount of pollution produced per minute while operating.
  """

  def __init__(self, name: str, craftSpeed: float, maxSlots: int,
               energyUsage: Watt, drain: Watt, pollution: int):
    self.name = name
    self.craftSpeed = craftSpeed
    self.maxSlots = maxSlots
    self.modules = [None] * self.maxSlots
    self.energyUsage = energyUsage
    self.drain = drain
    self.pollution = pollution

  def _getMultiplier(self, category: str) -> float:
    """Return the multiplier of the given category from module effects."""
    multiplier = 1
    for m in self.modules:
      if isinstance(m, Module):
        multiplier += m.__dict__[category]
    return multiplier

  def speedMultiplier(self) -> float:
    """Return the producer's crafting speed multiplier."""
    return self._getMultiplier('speed')

  def energyMultiplier(self) -> Watt:
    """Return the producer's energy usage multiplier."""
    return self._getMultiplier('energy')

  def productivityMultiplier(self) -> float:
    """Return the producer's added productivity multiplier."""
    return self._getMultiplier('productivity')

  def pollutionMultiplier(self) -> float:
    """Return the producer's pollution multiplier."""
    return self._getMultiplier('pollution')

  def craft(self, recipe: Recipe) -> dict:
    """Crafts the given input recipe with the producer's current stats.

    Returns a dict with the results of the craft: the craft duration, the
    recipe output, energy consumed and pollution produced.

    Parameters
    ----------
    recipe: Recipe
        The recipe to craft.
    """
    craftTime = recipe.time / self.craftSpeed * self.speedMultiplier()
    energyMult = self.energyMultiplier()
    energyConsumed = (self.drain + self.energyUsage * energyMult) * craftTime
    # FIXME: pollution value is per minute
    pollutionCreated = self.pollution * self.pollutionMultiplier() * energyMult

    return {'duration': craftTime, 'output': recipe.output,
            'energy': energyConsumed, 'pollution': pollutionCreated}

  def productionRate(self, recipe: Recipe, itemName: str,
                     count: int=1) -> float:
    """Return the rate that an item is produced, in items per second.

    Parameters
    ----------
    recipe: Recipe
        The recipe to examine.

    itemName: str
        The specific recipe product to obtain the production rate for.

    count: int, optional
        The number of identical producers concurrently crafting this recipe;
        acts as a multiplier. Defaults to one.
    """
    ingredient = recipe.getOutputByName[itemName]
    return count * ingredient.count / self.craft(recipe)['duration']

  def productionRateInverse(self, recipe: Recipe, itemName: str,
                            ips: float=1.0) -> float:
    """Return the number of these producers needed to reach the given rate.

    Parameters
    ----------
    recipe: Recipe
        The recipe to examine.

    itemName: str
        The specific recipe product being produced.

    ips: float, optional
        The target production rate to meet. Defaults to one item per second.
    """
    ingredient = recipe.getOutputByName(itemName)
    return ips * self.craft(recipe)['duration'] / ingredient.count

  def consumptionRate(self, recipe: Recipe, itemName: str,
                      count: int=1) -> float:
    """Return the rate that an item is consumed, in items per second.

    Parameters
    ----------
    recipe: Recipe
        The recipe to examine.

    itemName: str
        The specific recipe product to obtain the consumption rate for.

    count: int, optional
        The number of identical producers concurrently crafting this recipe;
        acts as a multiplier. Defaults to one.
    """
    ingredient = recipe.getInputByName(itemName)
    return count * ingredient.count / self.craft(recipe)['duration']

  def consumptionRateInverse(self, recipe: Recipe, itemName: str,
                            ips: float=1.0) -> float:
    """Return the number of these producers needed to reach the given rate.

    Parameters
    ----------
    recipe: Recipe
        The recipe to examine.

    itemName: str
        The specific recipe ingredient being consumed.

    ips: float, optional
        The target consumption rate to meet. Defaults to one item per second.
    """
    ingredient = recipe.getInputByName(itemName)
    return ips * self.craft(recipe)['duration'] / ingredient.count

  def rates(self, recipe: Recipe, count: int=1) -> dict:
    """Calculate all rates for this producer.

    Generates a report of every rate associated with this producer, such as
    energy consumption, pollution generated, individual items consumed and
    produced, etc.

    Parameters
    ----------
    recipe: Recipe
        The recipe to base the rates on.

    count: int, optional
        The number of identical producers concurrently crafting this recipe;
        acts as a multiplier. Defaults to one.
    """
    craftResult = self.craft(recipe)
    duration = craftResult['duration']
    consumed, produced = [], []
    for ingredient in recipe.input:
      name = ingredient.item.name
      consumed.append((ingredient, self.consumptionRate(recipe, name, count)))
    for ingredient in recipe.output:
      name = ingredient.item.name
      produced.append((ingredient, self.productionRate(recipe, name, count)))

    return {
      'producers': count,
      'consumed': consumed,
      'produced': produced,
      'energy': craftResult['energyConsumed'] / duration * count,
      'pollution': craftResult['pollutionCreated'] / duration * count
    }


class BurnerProducer(Producer, Burner):
  """Class representing a burner producer.

  A burner producer is simply a Producer that is powered by burning a Fuel.
  """

  def rates(self, recipe: Recipe, fuel: Fuel, count: int=1) -> dict:
    """Calculate all rates for this producer.

    Extended from the Producer base class to include fuel usage.

    Parameters
    ----------
    recipe: Recipe
        The recipe to base the rates on.

    fuel: factoratio.fuel.Fuel
        The fuel being burned.

    count: int, optional
        The number of identical producers concurrently crafting this recipe;
        acts as a multiplier. Defaults to one.
    """
    rateDict = super().__name__(recipe, count)
    rateDict['fuel'] = rateDict['energy'] / fuel.energy.value
    return rateDict

  def productsPerFuel(self, recipe: Recipe, itemName: str, fuel: Fuel,
                      count: int=1) -> float:
    """The number of items produced per unit of fuel burned.

    Parameters
    ----------
    recipe: Recipe
        The recipe to examine.

    itemName: str
        The specific recipe ingredient being produced.

    fuel: factoratio.fuel.Fuel
        The fuel being burned.

    count: int, optional
        The number of furnaces running concurrently. Defaults to one.
    """
    return (fuel.burnTime(self.energyConsumption)
            / self.productionRate(recipe, itemName, count))


class MiningDrill(Producer):
  """A class representing a mining drill.

  A mining drill is a Producer that consumes energy to extract a resource
  from the ground it is placed on.
  """

  def __getattribute__(self, name):
    if name in ['consumptionRate', 'consumptionRateInverse']:
      raise AttributeError
    return super().__getattribute__(name)

  def rates(self, recipe: Recipe, count: int=1):
    # TODO: consumption is n/a
    pass