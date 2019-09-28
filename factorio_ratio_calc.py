# Ratio calculator for Factorio

from collections import namedtuple
from enum import Enum, auto
import math

Craft = namedtuple('Craft', ['amount', 'time'])

class Fuel(Enum):
  """Energy amount in MJ of various fuels."""

  Wood = 2
  Coal = 4
  Solid = 12
  Rocket = 100
  Nuclear = 1210
  Uranium = 8000


class Module(Enum):
  """Speed, Productivity, and Efficiency Modules and their tiers."""

  Spd1 = auto()
  Spd2 = auto()
  Spd3 = auto()
  Pro1 = auto()
  Pro2 = auto()
  Pro3 = auto()
  Eff1 = auto()
  Eff2 = auto()
  Eff3 = auto()

def getSpeedMultiplier(modules: list) -> float:
  """Return the speed multiplier gained by the given list of modules."""

  speedMultiplier = 1
  if modules is not None:
    for m in modules:
      if m is Module.Spd1:
        speedMultiplier += 0.2
      elif m is Module.Spd2:
        speedMultiplier += 0.3
      elif m is Module.Spd3:
        speedMultiplier += 0.5
      elif m in (Module.Pro1, Module.Pro2, Module.Pro3):
        speedMultiplier -= 0.15
  return speedMultiplier


# TODO
def getProductivityMultiplier(modules: list) -> float:
  pass


def ips(sources: int, craft: Craft, modules: list=None) -> float:
  """Throughput of a craft in items per second (IPS).

  Gives total throughput of the craft distributed over a given number of sources.
  """

  return sources * craft.amount / (craft.time / getSpeedMultiplier(modules))


def ipsInverse(ips: float, craft: Craft, modules: list=None) -> float:
  """Number of consumers required to reach the given items per second (IPS).

  Based on the number of input items per run, and the duration of each run.
  """

  return ips * (craft.time / getSpeedMultiplier(modules)) / craft.amount


def minerIps(miners: int, modules: list=None) -> float:
  """Throughput of the given number of miners in items per second (IPS)."""

  miningSpeed = 0.5
  miningTime = 1 / (miningSpeed * getSpeedMultiplier(modules))

  return miners / miningTime


def minerIpsInverse(ips: float, modules: list=None) -> float:
  """Number of miners required to reach the given items per second (IPS)."""

  miningSpeed = 0.5
  miningTime = 1 / (miningSpeed * getSpeedMultiplier(modules))

  return ips * miningTime


def forgesGivenMiners(miners: int, craft: Craft) -> int:
  """Number of forges that can be sustained with the given number of miners."""

  return math.floor(ipsInverse(minerIps(miners), craft))


def minersGivenForges(forges: int, craft: Craft) -> int:
  """Number of miners needed to sustain the given number of forges."""

  return math.ceil(minerIpsInverse(ips(forges, craft)))


_suffixTable = {'k': 1e-3, 'm': 1, 'g': 1e3}

def fuelBurnTime(fuel: Fuel, consumption: str) -> float:
  """Burn time of a fuel at a given consumption rate.

  Consumption rate is given as a numeric string with optional SI suffix 'k',
  'm', or 'g' to specify kW, MW, or GW respectively. If no suffix is given,
  or if consumption is given as a number, kW are assumed for convenience.
  """

  if isinstance(consumption, str):
    mw = float(consumption[:-1]) * _suffixTable.get(consumption[-1], 1)
  else:
    mw = consumption * _suffixTable['k']

  # Joules -> kg*m^2 / s^2, Watts -> kg*m^2 / s^3; J/W give seconds
  return fuel.value / mw


def boilerFps(boilers: int, fuel: Fuel) -> float:
  """Fuel per second (FPS) consumed by the given number of boilers."""

  # 1 fuel / fuelBurnTime = 1 fuel/s
  # 1 fuel/s * n boilers = n / s
  # boilers = fuel since they burn 1 fuel at a time
  return boilers / fuelBurnTime(fuel, '1.8m')


def boilersGivenFps(fps: float, fuel: Fuel) -> int:
  """Number of boilers the given fuel per second (FPS) can sustain."""

  return math.floor(fps * fuelBurnTime(fuel, '1.8m'))


if __name__ == "__main__":
  import code
  code.interact(local=globals())