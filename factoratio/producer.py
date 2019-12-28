from factoratio.fuel import Burner, Fuel
from factoratio.item import Ingredient, Recipe
from factoratio.util import Joule, Watt

class Module():
  """A module for a Producer.

  Modifies various aspects of the Producer's operation including energy
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
    return (f'{__class__.__name__}({self.name!r}, {self.tier!r}, '
            f'{self.energy!r}, {self.speed!r}, {self.productivity!r}, '
            f'{self.pollution!r})')

  def __str__(self):
      return f'Tier {self.tier} {self.name} Module'


class Producer():
  """Base class for entities that produce an Item as output.

  Attributes
  ----------
  name: str
      The name of this Producer. Can be anything, but is typically the
      in-game name.

  craftSpeed: float
      The speed at which this Producer crafts a given Recipe; the Recipe
      crafting time is divided by this speed to yield the total crafting
      time.

  maxSlots: int
      The total number of module slots this Producer supports.

  energyUsage: factoratio.util.Watt
      The amount of energy consumed by this Producer per second while
      actively working, i.e. for the duration of a crafting cycle.

  drain: factoratio.util.Watt
      The amount of energy constantly consumed by this Producer, just by
      being connected to the power grid.

  pollution: float
      The amount of pollution produced per minute while operating.
  """

  def __init__(self, name: str, craftSpeed: float, maxSlots: int,
               energyUsage: Watt, drain: Watt, pollution: float):
    self.name = name
    self.craftSpeed = craftSpeed
    self.maxSlots = maxSlots
    self.modules = [None] * self.maxSlots
    self.energyUsage = energyUsage
    self.drain = drain
    self.pollution = pollution

  def __repr__(self):
    return (f'{self.__class__.__name__}({self.name!r}, {self.craftSpeed!r}, '
            f'{self.maxSlots!r}, {self.energyUsage!r}, {self.drain!r}, '
            f'{self.pollution!r})')

  def __str__(self):
    return self.name

  def _getMultiplier(self, category: str) -> float:
    """Return the multiplier of the given category from module effects."""
    multiplier = 1.0
    for m in self.modules:
      if isinstance(m, Module):
        multiplier += getattr(m, category)
    return round(multiplier, 6) # XXX: Hack around 1.1 + 0.1 and similar

  def speedMultiplier(self) -> float:
    """Return the Producer's crafting speed multiplier."""
    return self._getMultiplier('speed')

  def energyMultiplier(self) -> float:
    """Return the Producer's energy usage multiplier."""
    return self._getMultiplier('energy')

  def productivityMultiplier(self) -> float:
    """Return the Producer's added productivity multiplier."""
    return self._getMultiplier('productivity')

  def pollutionMultiplier(self) -> float:
    """Return the Producer's pollution multiplier."""
    return self._getMultiplier('pollution')

  def effectivePollutionMultiplier(self) -> float:
    """Return the Producer's effective pollution multiplier.

    The effective pollution multiplier is the product of the pollution and
    energy multipliers.
    """
    return self.pollutionMultiplier() * self.energyMultiplier()

  def craft(self, recipe: Recipe) -> dict:
    """Crafts the given input Recipe with the Producer's current stats.

    Returns a dict with the results of the craft: the craft duration, the
    Recipe output, energy consumed, and pollution produced.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to craft.
    """
    craftTime = recipe.time / (self.craftSpeed * self.speedMultiplier())
    energyMult = self.energyMultiplier()
    energyConsumed = Joule(
      (self.drain + self.energyUsage * energyMult).value) * craftTime
    # NOTE: Pollution stat is per minute
    pollutionCreated = (self.pollution * self.pollutionMultiplier() *
                       energyMult * (craftTime / 60))

    return {'duration': craftTime, 'output': recipe.output,
            'energy': energyConsumed, 'pollution': pollutionCreated}

  # TODO: For this and all subclasses, have itemName default to None, and pick the first output
  # actually, production functions don't need to care about WHICH output...
  def productionRate(self, recipe: Recipe, itemName: str,
                     count: int=1) -> float:
    """Return the rate that an Item is produced, in items per second.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to examine.

    itemName: str
        The specific Recipe product to obtain the production rate for.

    count: int, optional
        The number of identical Producers concurrently crafting this Recipe;
        acts as a multiplier. Defaults to one.
    """
    ingredient = recipe.getOutputByName(itemName)
    return (count * ingredient.count * self.productivityMultiplier()
            / self.craft(recipe)['duration'])

  def productionRateInverse(self, recipe: Recipe, itemName: str,
                            ips: float=1.0) -> float:
    """Return the number of these Producers needed to reach the given rate.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to examine.

    itemName: str
        The specific Recipe product being produced.

    ips: float, optional
        The target production rate to meet. Defaults to one item per second.
    """
    ingredient = recipe.getOutputByName(itemName)
    return (ips * self.craft(recipe)['duration'] /
            (ingredient.count * self.productivityMultiplier()))

  def consumptionRate(self, recipe: Recipe, itemName: str,
                      count: int=1) -> float:
    """Return the rate that an Item is consumed, in items per second.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to examine.

    itemName: str
        The specific Recipe product to obtain the consumption rate for.

    count: int, optional
        The number of identical Producers concurrently crafting this Recipe;
        acts as a multiplier. Defaults to one.
    """
    ingredient = recipe.getInputByName(itemName)
    return count * ingredient.count / self.craft(recipe)['duration']

  def consumptionRateInverse(self, recipe: Recipe, itemName: str,
                            ips: float=1.0) -> float:
    """Return the number of these Producers needed to reach the given rate.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to examine.

    itemName: str
        The specific Recipe ingredient being consumed.

    ips: float, optional
        The target consumption rate to meet. Defaults to one item per second.
    """
    ingredient = recipe.getInputByName(itemName)
    return ips * self.craft(recipe)['duration'] / ingredient.count

  def rates(self, recipe: Recipe, count: int=1) -> dict:
    """Calculate all rates for this Producer.

    Generates a report of every rate associated with this Producer, including
    energy consumption, pollution generated, individual items consumed and
    produced, and the count of Producers used.

    Rates are given as units per second.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to base the rates on.

    count: int, optional
        The number of identical Producers concurrently crafting this Recipe;
        acts as a multiplier. Defaults to one.
    """
    craftResult = self.craft(recipe)
    duration = craftResult['duration']
    consumed, produced = [], []
    for ingredient in recipe.input:
      name = ingredient.what.name
      consumed.append((ingredient, self.consumptionRate(recipe, name, count)))
    for ingredient in recipe.output:
      name = ingredient.what.name
      produced.append((ingredient, self.productionRate(recipe, name, count)))

    return {
      'producers': count,
      'consumed': consumed,
      'produced': produced,
      'energy': Watt(craftResult['energy'].value) / duration * count,
      'pollution': craftResult['pollution'] / duration * count
    }


class BurnerProducer(Producer, Burner):
  """Class representing a burner producer.

  A burner producer is simply a Producer that is powered by burning a Fuel.
  """

  def rates(self, recipe: Recipe, fuel: Fuel, count: int=1) -> dict:
    """Calculate all rates for this Producer.

    Extended from the Producer base class to include the amount of Fuel
    burned.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to base the rates on.

    fuel: factoratio.fuel.Fuel
        The fuel being burned.

    count: int, optional
        The number of identical Producers concurrently crafting this Recipe;
        acts as a multiplier. Defaults to one.
    """
    rateDict = super().rates(recipe, count)
    rateDict['fuel'] = rateDict['energy'].value / fuel.energy.value
    return rateDict

  def productsPerFuel(self, recipe: Recipe, itemName: str, fuel: Fuel,
                      count: int=1) -> float:
    """The number of Items produced per unit of Fuel burned.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to examine.

    itemName: str
        The specific Recipe ingredient being produced.

    fuel: factoratio.fuel.Fuel
        The Fuel being burned.

    count: int, optional
        The number of Producers running concurrently. Defaults to one.
    """
    return (fuel.burnTime(self.energyUsage)
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
    """Return the rate that an Item is produced, in items per second.

    Typically Recipe.miningRecipe is used to construct the Recipe object, but
    this is not a hard requirement.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to examine.

    itemName: str, optional
        The specific Recipe product to obtain the production rate for. If
        unspecified, assumes the output item as long as it's the only
        product.

    count: int, optional
        The number of identical Producers concurrently crafting this Recipe;
        acts as a multiplier. Defaults to one.
    """
    if itemName is None:
      if len(recipe.output) == 1:
        itemName = recipe.output[0].what.name
      else:
        raise ValueError('Cannot use default itemName value when output '
                         'contains more than one product.')
    return super().productionRate(recipe, itemName, count)

  def productionRateInverse(self, recipe: Recipe, itemName: str=None,
                            ips: float=1.0) -> float:
    """Return the number of these Producers needed to reach the given rate.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to examine.

    itemName: str, optional
        The specific Recipe product being produced. If unspecified, assumes
        the output item as long as it's the only product.

    ips: float, optional
        The target production rate to meet. Defaults to one item per second.
    """
    if itemName is None:
      if len(recipe.output) == 1:
        itemName = recipe.output[0].what.name
      else:
        raise ValueError('Cannot use default itemName value when output '
                         'contains more than one product.')
    return super().productionRateInverse(recipe, itemName, ips)

  def consumptionRate(self, recipe: Recipe, itemName: str=None,
                      count: int=1) -> float:
    """Return the rate that an Item is consumed, in items per second.

    Mining drills typically only "consume" the resource that they're placed
    on top of, which is equivalent to its output. Typically
    Recipe.miningRecipe is used to construct the Recipe object, but this is
    not a hard requirement.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to examine, usually from Recipe.miningRecipe.

    itemName: str, optional
        The specific Recipe product to obtain the consumption rate for. If
        unspecified, assumes the output item as long as it's the only
        product.

    count: int, optional
        The number of identical Producers concurrently crafting this Recipe;
        acts as a multiplier. Defaults to one.
    """
    if itemName is None:
      if len(recipe.output) == 1:
        itemName = recipe.output[0].what.name
      else:
        raise ValueError('Cannot use default itemName value when output '
                         'contains more than one product.')
    return super().consumptionRate(recipe, itemName, count)

  def consumptionRateInverse(self, recipe: Recipe, itemName: str,
                            ips: float=1.0) -> float:
    """Return the number of these Producers needed to reach the given rate.

    Mining drills typically only "consume" the resource that they're placed
    on top of, which is equivalent to its output. Typically
    Recipe.miningRecipe is used to construct the Recipe object, but this is
    not a hard requirement.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to examine, usually from Recipe.miningRecipe.

    itemName: str, optional
        The specific Recipe ingredient being consumed. If unspecified,
        assumes the output product as long as it's the only product, since
        the miner consumes from the ground what it produces.

    ips: float, optional
        The target consumption rate to meet. Defaults to one per second.
    """
    if itemName is None:
      if len(recipe.output) == 1:
        ingredient = recipe.output[0].what.name
      else:
        raise ValueError('Cannot use default itemName value when output '
                         'contains more than one product.')
    return super().consumptionRateInverse(recipe, itemName, ips)

  def rates(self, recipe: Recipe, count: int=1) -> dict:
    """Calculate all rates for this Producer.

    Generates a report of every rate associated with this Producer, including
    energy consumption, pollution generated, individual items consumed and
    produced, and the count of Producers used.

    Rates are given as units per second.

    For mining drills, the "consumption" is the same as its production unless
    it has extra inputs or outputs.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to base the rates on, usually from Recipe.miningRecipe.

    count: int, optional
        The number of identical Producers concurrently crafting this Recipe;
        acts as a multiplier. Defaults to one.
    """
    rateDict = super().rates(recipe, count)
    if not rateDict['consumed']:
      rateDict['consumed'] = rateDict['produced']
    return rateDict


class BurnerMiningDrill(MiningDrill, BurnerProducer):
  """A class representing a burner mining drill.

  A burner mining drill is simply a MiningDrill that is powered by burning a
  Fuel.
  """
  pass


class Pumpjack(Producer):
  """A class representing a Pumpjack.

  Pumpjacks are placed on an oil field and extract crude oil at a constant
  rate, the amount depending on the field's yield.

  Most methods inherited from Producer have had their behavior modified to
  suit the Pumpjack's behavior.
  """

  def productionRate(self, recipe: PumpjackRecipe, currentYield: int,
                     count: int=1):
    """Return the rate that a Fluid is produced, in fluid per second.

    The amount of fluid that a Pumpjack returns is dependent on the yield of
    the field that it is placed on, which is given as a percentage. The
    amount of fluid pumped per cycle is equal to X times the yield, where X
    is the base amount of a particular fluid returned from any field. For
    example, given a yield of 538% and a base amount of 10, one cycle
    produces 54 fluid.

    Every 1% of yield is equal to 300 cycles, with fields having a minimum
    yield of 20%. Output is limited to 100 fluid per cycle.

    Parameters
    ----------
    recipe: PumpjackRecipe
        The Recipe to examine.

    currentYield: int
        The current yield of the field that this Pumpjack is placed on. Given
        as an integer percentage, e.g. 250 for 250%.

    count: int, optional
        The number of identical Producers concurrently crafting this Recipe;
        acts as a multiplier. Defaults to one.
    """
    # TODO: Determine if productivity bonus can exceed the 100 cap
    return (min(currentYield / recipe.baseAmt, 100) * self.productivityMultiplier()
            * count / self.craft(recipe)['duration'])

  def productionRateInverse(self, recipe: PumpjackRecipe, currentYield: int,
                            fps: float=1.0) -> float:
    """Return the number of these Pumpjacks needed to reach the given rate.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to examine.

    currentYield: int
        The current yield of field that this Pumpjack is placed on. Given as
        an integer percentage, e.g. 250 for 250%.

    fps: float, optional
        The target production rate to meet. Defaults to one fluid per second.
    """
    return (fps * self.craft(recipe)['duration'] /
            (min(currentYield / recipe.baseAmt, 100) * self.productivityMultiplier()))

  def consumptionRate(self, recipe: PumpjackRecipe, count: int=1) -> float:
    """Returns the rate at which 1% of a field's yield is depleted.

    This rate is given per minute, unlike other rates. Each Pumpjack cycle
    reduces the field's yield by 1% every 300 cycles.

    Parameters
    ----------
    recipe: PumpjackRecipe
        The Recipe to examine.

    count: int, optional
        The number of identical Producers concurrently crafting this Recipe;
        acts as a multiplier. Defaults to one.
    """
    return 1 / self.craft(recipe)['duration'] / 300 * 60 * count

  def consumptionRateInverse(self, recipe: PumpjackRecipe,
                             ypm: float=1) -> float:
    """Return the number of these Pumpjacks needed to reach the given rate.

    Parameters
    ----------
    recipe: PumpjackRecipe
        The recipe to examine.

    ypm: float
        The desired yield per minute consumed.
    """
    return ypm * self.craft(recipe)['duration'] * 300 / 60

  def rates(self, recipe: PumpjackRecipe, count: int=1) -> dict:
    """Calculate all rates for this Pumpjack.

    Generates a report of every rate associated with this Pumpjack, including
    energy consumption, pollution generated, yield consumed, field cycles
    consumed, fluid extracted, and the count of Pumpjacks used.

    Rates are given as units per second, except yield consumption, which is
    per minute.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to base the rates on, usually from Recipe.miningRecipe.

    count: int, optional
        The number of identical Producers concurrently crafting this Recipe;
        acts as a multiplier. Defaults to one.
    """
    rateDict = super().rates(recipe, count)
    rateDict['cycles'] = self.fieldCycleConsumptionRate(recipe, count)

  def fieldCycleConsumptionRate(self, recipe: PumpjackRecipe,
                                count: int=1) -> float:
    """Return the rate at which a field's cycles are consumed.

    The rate is given per second. Each Pumpjack cycle reduces the field's
    yield by 1% every 300 cycles.

    Parameters
    ----------
    recipe: Recipe
        The Recipe to base the rates on, usually from Recipe.miningRecipe.

    count: int, optional
        The number of identical Producers concurrently crafting this Recipe;
        acts as a multiplier. Defaults to one.
    """
    return self.craftSpeed * self.speedMultiplier() / recipe.time * count


base = {
  'Assembler1': Producer('Assembling machine', 0.5, 0, Watt('75k'), Watt('2.5k'), 4),
  'Assembler2': Producer('Assembling machine 2', 0.75, 2, Watt('150k'), Watt('5k'), 3),
  'Assembler3': Producer('Assembling machine 3', 1.25, 4, Watt('375k'), Watt('12.5k'), 2),
  'BurnDrill': BurnerMiningDrill('Burner mining drill', 0.25, 0, Watt('150k'), 0, 12),
  'ElecDrill': MiningDrill('Electric mining drill', 0.5, 3, Watt('90k'), 0, 10),
  'StoneFurance': BurnerProducer('Stone furnace', 1, 0, Watt('90k'), 0, 2),
  'SteelFurance': BurnerProducer('Steel furnace', 2, 0, Watt('90k'), 0, 4),
  'ElecFurance': Producer('Electric furnace', 2, 2, Watt('180k'), Watt('6k'), 1),
  'ChemPlant': Producer('Chemical plant', 1, 3, Watt('210k'), Watt('7k'), 4),
  'Pumpjack': Pumpjack('Pumpjack', 1, 2, Watt('90k'), 0, 10)
}

# TODO: Find a place for these prototype functions

# def forgesGivenMiners(miners: int, craft: Craft) -> int:
#   """Number of forges that can be sustained with the given number of miners."""
#   return math.floor(ipsInverse(minerIps(miners), craft))

# def minersGivenForges(forges: int, craft: Craft) -> int:
#   """Number of miners needed to sustain the given number of forges."""
#   return math.ceil(minerIpsInverse(ips(forges, craft)))