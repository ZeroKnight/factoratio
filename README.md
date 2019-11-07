# Factoratio

An assistive tool for calculating and reporting ideal ratios and resource
usage for arbitrary assembly setups in Factorio, a game by Wube Software LTD.

## Under Development

This program is currently under development and is still in an early phase.
While some ratio calculations are implemented to varying degrees, there is
currently no user interface. That said, feel free to poke about.

## Planned Direction and Features

As its name would suggest, Factoratio's primary feature set will revolve
around calculating and experimenting with ideal assembly ratios, given an
arbitrary set of producers and/or consumers with possibly varying stats and a
desired product set. However, Factoratio aims to support calculation of
ratios regarding virtually every aspect in Factorio, including fuel
consumption and burn times, power generation, and more.

Beyond that, Factoratio will also report related information including, but not limited to:

  * Consumption of energy, fuel, liquids, and materials, pollution
    * Per crafting cycle
    * Per unit of time (ticks, seconds, minutes, hours, etc.)

  * Counts of machines and utilities used, such as assemblers, belts,
    inserters, mining drills, and so on

  * Support for inverse operations

  * Pulls item and recipe definitions right from an installed copy of Factorio,
    or the official [wube/factorio-data repository](https://github.com/wube/factorio-data)

  * And more...