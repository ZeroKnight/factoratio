from dataclasses import dataclass
from typing import Union

from factoratio.util import Joule, Watt

@dataclass
class Fuel():
  """Class representing a fuel source.

  A Fuel is burned to produce energy in "burner" devices; it acts as a power
  source for non-electrical devices.

  Attributes
  ----------
  name: str
      The name of the fuel.

  energy: factoratio.util.Joule
      The total energy contained in the fuel, in Joules.
  """

  name: str
  energy: Union[Joule, str]

  def __post_init__(self):
    if isinstance(self.energy, str):
      self.energy = Joule(self.energy)
    else:
      raise TypeError('energy must be of type str or Joule')

  def __str__(self):
    return f'{self.name}'

  def burnTime(self, consumptionRate: Watt, count: int=1) -> float:
    """Burn time of this fuel at the given energy consumption rate.

    Returns the total time in seconds that the given number of units of this
    fuel will burn at the specified rate. Defaults to one.
    """
    # Joules -> kg*m^2 / s^2 | Watts -> kg*m^2 / s^3
    return self.energy.value / consumptionRate.value * count

  def fuelBurnedInTime(self, consumptionRate: Watt, time: float) -> float:
    """How much of this fuel will be burned in the given time and rate.

    Returns the amount of fuel burned if consumed at the given rate for the
    given amount of time.
    """
    return time / self.burnTime(consumptionRate)


class Burner():
  """A mixin representing a device that burns fuel for power.

  As opposed to other devices that directly run on electrical power, burner
  devices consume a fuel source at a constant rate while operational.

  The mixed class must implement an energyUsage attribute for this mixin to
  have any use.
  """

  def fuelConsumptionRate(self, fuel: Fuel, count: int=1) -> float:
    """The amount of the given fuel this burner will consume per second.

    Parameters
    ----------
    fuel: factoratio.fuel.Fuel
        The fuel being burned.

    count: int, optional
        The amount of burners running concurrently. Defaults to one.
    """
    # 1 fuel / burnTime = 1 fuel/s
    # 1 fuel/s * n burners = n / s
    # burners = fuel since they burn 1 fuel at a time
    return count / fuel.burnTime(self.energyUsage)

  def fuelConsumptionRateInverse(self, rate: float, fuel: Fuel) -> float:
    """The number of burners required to reach the given rate.

    Parameters
    ----------
    rate: float
        The rate at which the given fuel is burned per second.

    fuel: factoratio.fuel.Fuel
        The fuel being burned.
    """
    return rate * fuel.burnTime(self.energyUsage)
