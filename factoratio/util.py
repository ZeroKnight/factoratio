"""util.py

Miscellaneous utility functions and clases.
"""

import functools
import logging
import math
from pathlib import Path
import sys
from typing import Union
from xdgappdirs import user_config_dir

from factoratio import APPNAME

logger = logging.getLogger('factoratio')

def getConfigPath(path: Path=None) -> Path:
  """Returns a Path object relative to the user configuration directory."""

  configDir = user_config_dir(APPNAME, appauthor=False, roaming=True,
                               as_path=True)
  return configDir.joinpath(path or '')

def getSteamLibraries(steamPath: Path) -> list:
  """Retrieve a list of Steam library paths.

  Given the path to a Steam installation, and by extension the primary
  library, return a list containing the primary library and any extra
  libraries listed in steamapps/libraryfolders.vdf.

  Parameters
  ----------
  steamPath: Path
      The path to a Steam installation, e.g. Path(r'C:\Program Files\Steam').
  """
  lfPath = steamPath / 'steamapps' / 'libraryfolders.vdf'
  if not lfPath.exists():
    raise FileNotFoundError('Could not find libraryfolders.vdf in the Steam '
                            f"installation at '{steamPath}'")
  libraries = [steamPath]
  with lfPath.open() as lf:
    for line in lf:
      parts = line.replace('"', '').split()
      if parts[0].isdigit():
        libraries.append(Path(parts[1]))
  return libraries

def getFactorioPath():
  steamPath = fallbackSteamPath = None
  # Check for Steam version
  if sys.platform == 'win32':
    import winreg
    try:
      with winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER,
      r'Software\Valve\Steam') as key:
        steamPath = Path(winreg.QueryValueEx(key, 'SteamPath')[0])
    except FileNotFoundError as err:
      logger.debug('Registry lookup for Steam installation failed: ', err)
  elif sys.platform == 'linux':
    # NOTE: Some people move Steam from the default install location, which the
    # Steam client seems to support, as it will ask where its files are.
    # /usr/bin/steam is actually a wrapper script that points Steam in the
    # right places. I believe that the the wrapper/bootstrap points the
    # ~/.steam/steam symlink to the proper Steam installation, so we can use it
    # as a fallback if the default path is invalid.
    steamPath = Path.home() / '.local' / 'share' / 'Steam'
    fallbackSteamPath = Path.home() / '.steam' / 'steam'
    if not steamPath.exists():
      logger.warning(f'No Steam installation found at the default path '
                      f'({steamPath}). Attempting to fall back to '
                      f"'{fallbackSteamPath}'")
      steamPath = fallbackSteamPath if fallbackSteamPath.exists() else None

  if steamPath is not None:
    for library in getSteamLibraries(steamPath):
      factorioPath = library / 'steamapps' / 'common' / 'Factorio'
      if factorioPath.exists():
        return factorioPath
  else:
    logger.debug('Could not find Steam installation; attempting to find the '
                  'stand-alone installation...')

  # Check for stand-alone version
  if sys.platform == 'win32':
    try:
      key = winreg.OpenKeyEx(winreg.HKEY_LOCAL_MACHINE,
        r'Software\Microsoft\Windows\CurrentVersion\Uninstall\Factorio_is1')
      factorioPath = winreg.QueryValueEx(key, 'InstallLocation')
    except FileNotFoundError as err:
      logger.debug('Registry lookup for Steam installation failed: ', err)
  elif sys.platform == 'linux':
    logger.warning('Stand-alone installation lookup is not supported on '
                    'Linux, as it is just a simple tarball.')
  if factorioPath.exists():
    return factorioPath
  else:
    logger.warning('Could not find a stand-alone installation!')
    return None


class SINumber():
  """A class representing an arbitrary unit number supporting SI suffixes.

  Can be constructed with a string consisting of a real number or integer and
  an optional SI suffix that multiplies the given number. Only suffixes
  common to Factorio are supported; they are: k, M, G, and T.

  Attributes
  ----------
  value: float
      The scalar value representing the quantity of the unit.

  baseSymbol: str
      Short string representing the base unit, e.g. 'W' for Watts.

  origSuffix: str
      The SI suffix originally used to specify the magnitude of the unit.
  """

  _suffixTable = {'k': 1e3, 'm': 1e6, 'g': 1e9, 't': 1e12}

  def _unitOrNumber(func):
    """Internal decorator for implementing special methods.

    Slightly alters the exact method depending on whether the other side is a
    unit number or some other number.
    """
    @functools.wraps(func)
    def wrapper(self, other=None):
      if other is None:
        return func(self)
      if isinstance(other, (self.__class__, SINumber)):
        return func(self, other.value)
      else:
        return func(self, other)
    return wrapper

  def __init__(self, units: Union[str, int, float], baseSymbol: str):
    self.baseSymbol = baseSymbol
    if isinstance(units, str):
      if units[-1].casefold() == self.baseSymbol.casefold():
        units = units[:-1]
      try:
        suffix = units[-1].casefold()
      except IndexError:
        raise ValueError('units string cannot be empty')
      try:
        scalar = float(units[:-1]) if suffix.isalpha() else float(units)
      except ValueError:
        raise ValueError('units string must contain a valid number')
      if suffix.isalpha():
        if suffix in self._suffixTable:
          scalar *= self._suffixTable[suffix]
          self.origSuffix = suffix
        else:
          raise ValueError(f"Invalid suffix: '{suffix}'")
      self.value = scalar
    elif isinstance(units, (int, float)):
      self.value = units

  def __repr__(self):
    return f'{self.__class__.__name__}({self.value!r})'

  def __str__(self):
    # Adapted from https://stackoverflow.com/a/29749228/1208424
    if self.value == 0:
      return f'0{self.baseSymbol}'

    # Limit to TW
    power = min(12, math.floor(math.log10(abs(self.value))))
    d, m = divmod(power, 3)
    reduced = self.value * 10**(m - power)

    return f"{reduced:.4} {' kMGT'[d] if d > 0 else ''}{self.baseSymbol}"

  @_unitOrNumber
  def __eq__(self, other) -> bool:
    return self.value == other

  def __bool__(self) -> bool:
    return bool(self.value)

  @_unitOrNumber
  def __add__(self, other):
    return self.__class__(self.value + other)
  __radd__ = __add__

  @_unitOrNumber
  def __sub__(self, other):
    return self.__class__(self.value - other)

  @_unitOrNumber
  def __rsub__(self, other):
    return self.__class__(other - self.value)

  @_unitOrNumber
  def __mul__(self, other):
    return self.__class__(self.value * other)
  __rmul__ = __mul__

  @_unitOrNumber
  def __truediv__(self, other):
    return self.__class__(self.value / other)

  @_unitOrNumber
  def __rtruediv__(self, other):
    return self.__class__(other / self.value)

  @_unitOrNumber
  def __floordiv__(self, other):
    return self.__class__(self.value // other)

  @_unitOrNumber
  def __rfloordiv__(self, other):
    return self.__class__(other // self.value)

  @_unitOrNumber
  def __mod__(self, other):
    return self.__class__(self.value % other)

  @_unitOrNumber
  def __rmod__(self, other):
    return self.__class__(other % self.value)

  @_unitOrNumber
  def __divmod__(self, other):
    cl = self.__class__
    return cl(self.value / other), cl(self.value % other)

  @_unitOrNumber
  def __rdivmod__(self, other):
    cl = self.__class__
    return cl(other / self.value), cl(other % self.value)

  @_unitOrNumber
  def __pow__(self, other, modulo=None):
    if modulo is None:
      return self.__class__(self.value ** other)
    else:
      return self.__class__(pow(self.value, other, modulo))

  @_unitOrNumber
  def __rpow__(self, other, modulo=None):
    if modulo is None:
      return self.__class__(other ** self.value)
    else:
      return self.__class__(pow(other, self.value, modulo))

  @_unitOrNumber
  def __iadd__(self, other):
    self.value += other
    return self.value

  @_unitOrNumber
  def __isub__(self, other):
    self.value -= other
    return self.value

  @_unitOrNumber
  def __imul__(self, other):
    self.value *= other
    return self.value

  @_unitOrNumber
  def __itruediv__(self, other):
    self.value /= other
    return self.value

  @_unitOrNumber
  def __ifloordiv__(self, other):
    self.value //= other
    return self.value

  @_unitOrNumber
  def __imod__(self, other):
    self.value %= other
    return self.value

  @_unitOrNumber
  def __ipow__(self, other, modulo=None):
    if modulo is None:
      self.value **= other
    else:
      self.value = pow(self.value, other, modulo)
    return self.value

  def __neg__(self):
    return self.__class__(-self.value)

  def __abs__(self):
    return self.__class__(abs(self.value))

  def __int__(self):
    return int(self.value)

  def __float__(self):
    return float(self.value)

  _unitOrNumber = staticmethod(_unitOrNumber)


class Watt(SINumber):
  """A class representing a Watt unit supporting SI suffixes."""

  def __init__(self, watts: Union[str, int, float]):
    super().__init__(watts, 'W')


class Joule(SINumber):
  """A class representing a Joule unit supporting SI suffixes."""

  def __init__(self, joules: Union[str, int, float]):
    super().__init__(joules, 'J')