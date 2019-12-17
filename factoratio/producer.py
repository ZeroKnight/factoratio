from factoratio.fuel import Burner, Fuel
from factoratio.item import Ingredient, Recipe
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
        multiplier += getattr(m, category)
    return multiplier

  def speedMultiplier(self) -> float:
    """Return the producer's crafting speed multiplier."""
    return self._getMultiplier('speed')

  def energyMultiplier(self) -> float:
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
    recipe output, energy consumed, and pollution produced.

    Parameters
    ----------
    recipe: Recipe
        The recipe to craft.
    """
    craftTime = recipe.time / self.craftSpeed * self.speedMultiplier()
    energyMult = self.energyMultiplier()
    energyConsumed = (self.drain + self.energyUsage * energyMult) * craftTime
    # NOTE: Pollution stat is per minute
    pollutionCreated = (self.pollution * self.pollutionMultiplier() *
                       energyMult * (craftTime / 60))

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
    ingredient = recipe.getOutputByName(itemName)
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
      'energy': craftResult['energy'] / duration * count,
      'pollution': craftResult['pollution'] / duration * count
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
    rateDict = super().rates(recipe, count)
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

  Most methods inherited from Producer have had their behavior slightly
  modified to suit the more basic nature of vanilla Factorio mining recipes.
  See also: Recipe.miningRecipe.
  """

  def productionRate(self, recipe: Recipe, itemName: str=None,
                     count: int=1) -> float:
    """Return the rate that an item is produced, in items per second.

    Typically Recipe.miningRecipe is used to construct the Recipe object, but
    this is not a hard requirement.

    Parameters
    ----------
    recipe: Recipe
        The recipe to examine.

    itemName: str, optional
        The specific recipe product to obtain the production rate for. If
        unspecified, assumes the output item as long as it's the only
        product.

    count: int, optional
        The number of identical producers concurrently crafting this recipe;
        acts as a multiplier. Defaults to one.
    """
    if itemName is None:
      if len(recipe.output) == 1:
        itemName = recipe.output[0].item.name
      else:
        raise ValueError('Cannot use default itemName value when output '
                         'contains more than one product.')
    return super().productionRate(recipe, itemName, count)

  def productionRateInverse(self, recipe: Recipe, itemName: str=None,
                            ips: float=1.0) -> float:
    """Return the number of these producers needed to reach the given rate.

    Parameters
    ----------
    recipe: Recipe
        The recipe to examine.

    itemName: str
        The specific recipe product being produced. If unspecified, assumes
        the output item as long as it's the only product.

    ips: float, optional
        The target production rate to meet. Defaults to one item per second.
    """
    if itemName is None:
      if len(recipe.output) == 1:
        itemName = recipe.output[0].item.name
      else:
        raise ValueError('Cannot use default itemName value when output '
                         'contains more than one product.')
    return super().productionRateInverse(recipe, itemName, ips)

  def consumptionRate(self, recipe: Recipe, itemName: str=None,
                      count: int=1) -> float:
    """Return the rate that an item is consumed, in items per second.

    Mining drills typically only "consume" the resource that they're placed
    on top of, which is equivalent to its output. Typically
    Recipe.miningRecipe is used to construct the Recipe object, but this is
    not a hard requirement.

    Parameters
    ----------
    recipe: Recipe
        The recipe to examine, usually from Recipe.miningRecipe.

    itemName: str, optional
        The specific recipe product to obtain the consumption rate for. If
        unspecified, assumes the output item as long as it's the only
        product.

    count: int, optional
        The number of identical producers concurrently crafting this recipe;
        acts as a multiplier. Defaults to one.
    """
    if itemName is None:
      if len(recipe.output) == 1:
        itemName = recipe.output[0].item.name
      else:
        raise ValueError('Cannot use default itemName value when output '
                         'contains more than one product.')
    return super().consumptionRate(recipe, itemName, count)

  def consumptionRateInverse(self, recipe: Recipe, itemName: str,
                            ips: float=1.0) -> float:
    """Return the number of these producers needed to reach the given rate.

    Mining drills typically only "consume" the resource that they're placed
    on top of, which is equivalent to its output. Typically
    Recipe.miningRecipe is used to construct the Recipe object, but this is
    not a hard requirement.

    Parameters
    ----------
    recipe: Recipe
        The recipe to examine, usually from Recipe.miningRecipe.

    itemName: str, optional
        The specific recipe ingredient being consumed. If unspecified,
        assumes the output product as long as it's the only product, since
        the miner consumes from the ground what it produces.

    ips: float, optional
        The target consumption rate to meet. Defaults to one per second.
    """
    if itemName is None:
      if len(recipe.output) == 1:
        ingredient = recipe.output[0].item.name
      else:
        raise ValueError('Cannot use default itemName value when output '
                         'contains more than one product.')
    return super().consumptionRateInverse(recipe, itemName, ips)

  def rates(self, recipe: Recipe, count: int=1) -> dict:
    """Calculate all rates for this producer.

    Generates a report of every rate associated with this producer, such as
    energy consumption, pollution generated, individual items consumed and
    produced, etc.

    For mining drills, the "consumption" is the same as its production unless
    it has extra inputs or outputs.

    Parameters
    ----------
    recipe: Recipe
        The recipe to base the rates on, usually from Recipe.miningRecipe.

    count: int, optional
        The number of identical producers concurrently crafting this recipe;
        acts as a multiplier. Defaults to one.
    """
    rateDict = super().rates(recipe, count)
    if not rateDict['consumed']:
      rateDict['consumed'] = rateDict['produced']
    return rateDict


class BurnerMiningDrill(MiningDrill, Burner):
  """A class representing a burner mining drill.

  A burner mining drill is simply a MiningDrill that is powered by burning a
  Fuel.
  """
  pass


# TODO: Find a place for these prototype functions

# def forgesGivenMiners(miners: int, craft: Craft) -> int:
#   """Number of forges that can be sustained with the given number of miners."""
#   return math.floor(ipsInverse(minerIps(miners), craft))

# def minersGivenForges(forges: int, craft: Craft) -> int:
#   """Number of miners needed to sustain the given number of forges."""
#   return math.ceil(minerIpsInverse(ips(forges, craft)))