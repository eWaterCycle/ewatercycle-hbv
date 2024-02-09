"""Forcing related functionality for HBV."""
# Based on https://github.com/eWaterCycle/ewatercycle-marrmot/blob/main/src/ewatercycle_marrmot/forcing.py

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import xarray as xr
import numpy as np

from ewatercycle.base.forcing import DefaultForcing
# from ewatercycle.esmvaltool.builder import RecipeBuilder
from ewatercycle.esmvaltool.schema import Dataset, Recipe


class HBVForcing(DefaultForcing):
    """Container for HBV forcing data.

    Args:
        directory: Directory where forcing data files are stored.
        start_time: Start time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        end_time: End time of forcing in UTC and ISO format string e.g.
            'YYYY-MM-DDTHH:MM:SSZ'.
        shape: Path to a shape file. Used for spatial selection.
        forcing_file: .txt file that contains forcings for HBV model including precipitation and evaporation
                    contains columns: ["year", "month", "day", "pr", "pev"] seperated by a space
        precipitation_file: xarray containing precipition
        potential_evaporation_file: xarray containing potential evaporation, same format as above
        # TODO add beter desription of type
    Examples:

        From existing forcing data:

        .. code-block:: python

            from ewatercycle.forcing import sources

            forcing = sources.HBVForcing(
                directory='/home/davidhaasnoot/Code/Forcing/',
                start_time='1989-01-02T00:00:00Z',
                end_time='1999-01-02T00:00:00Z',
                forcing_file='forcing.txt',
                precipitation_file="precipitation_file.nc"
                precipitation_file="precipitation.nc"
            )
    """


    forcing_file: Optional[str] = "forcing.txt"

    # @classmethod
    # def _build_recipe(
    #     cls,
    #     start_time: datetime,
    #     end_time: datetime,
    #     shape: Path,
    #     dataset: Dataset | str | dict,
    #     **model_specific_options,
    # ):
    #     return build_marrmot_recipe(
    #         start_year=start_time.year,
    #         end_year=end_time.year,
    #         shape=shape,
    #         dataset=dataset,
    #     )

    # TODO Implement this to take .txt and add them?
    def to_xarray(self) -> xr.Dataset:
        """Load forcing data from a txt file into an xarray dataset.

        Returns:
            Dataset with forcing data.
        """
        if self.directory is None or self.forcing_file is None:
            raise ValueError("Directory or forcing_file is not set")
        fn = self.directory / self.forcing_file
        forcing = np.loadtxt(fn, delimiter="	")
        names = ["year", "month", "day", "pr", "pev"]
        df_in = pd.DataFrame(forcing, columns=names)
        df_in.index = df_in.apply(lambda x: pd.Timestamp(f'{int(x.year)}-{int(x.month)}-{int(x.day)}'), axis=1)
        df_in.drop(columns=["year", "month", "day"], inplace=True)
        df_in.index.name = "time"
        # TODO use netcdf-cf conventions
        ds = xr.Dataset(data_vars=df_in,
                        attrs={
                            "title": "HBV forcing data",
                            "history": "Created by ewatercycle_HBV.forcing.HBVForcing.to_xarray()",
                                },
                        )
        return ds

# TODO add generate from ERA5 forcing dataset and Rhine.
"""
.. code-block:: python

    from ewatercycle.forcing import sources
    from ewatercycle.testing.fixtures import rhine_shape

    shape = rhine_shape()
    forcing = sources.MarrmotForcing.generate(
        dataset='ERA5',
        start_time='2000-01-01T00:00:00Z',
        end_time='2001-01-01T00:00:00Z',
        shape=shape,
    )
"""
# def build_marrmot_recipe(
#     start_year: int,
#     end_year: int,
#     shape: Path,
#     dataset: Dataset | str | dict,
# ) -> Recipe:
#     """Build an ESMValTool recipe for generating forcing for MARRMoT.
#
#     Args:
#         start_year: Start year of forcing.
#         end_year: End year of forcing.
#         shape: Path to a shape file. Used for spatial selection.
#         dataset: Dataset to get forcing data from.
#             When string is given a predefined dataset is looked up in
#             :py:const:`ewatercycle.esmvaltool.datasets.DATASETS`.
#             When dict given it is passed to
#             :py:class:`ewatercycle.esmvaltool.models.Dataset` constructor.
#     """
#     return (
#         RecipeBuilder()
#         .title("Generate forcing for the MARRMoT hydrological model")
#         .description("Generate forcing for the MARRMoT hydrological model")
#         .dataset(dataset)
#         .start(start_year)
#         .end(end_year)
#         .shape(shape)
#         # TODO do lumping in recipe preprocessor instead of in diagnostic script
#         # .lump()
#         .add_variables(("tas", "pr", "psl", "rsds"))
#         .add_variable("rsdt", mip="CFday")
#         .script(
#             str((Path(__file__).parent / "forcing_diagnostic_script.py").absolute()),
#             {"basin": shape.stem})
#         .build()
#     )