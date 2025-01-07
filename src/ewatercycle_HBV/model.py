"""eWaterCycle wrapper for the HBV model."""
import json
from collections.abc import ItemsView
from pathlib import Path
from typing import Any, Type

from ewatercycle.forcing import LumpedMakkinkForcing, CaravanForcing

from ewatercycle.base.model import (
    ContainerizedModel,
    eWaterCycleModel,
    LocalModel,
    )
from ewatercycle.container import ContainerImage
from bmipy import Bmi

def import_bmi():
    """"Import BMI, raise useful exception if not found"""
    try:
        from HBV import HBV as HBV_bmi
    except ModuleNotFoundError:
        msg = (
            "HBV bmi package not found, install using: `pip install HBV`"
        )
        raise ModuleNotFoundError(msg)

    return HBV_bmi

HBV_PARAMS = (
    "Imax",
    "Ce",
    "Sumax",
    "Beta",
    "Pmax",
    "Tlag",
    "Kf",
    "Ks",
    "FM",
)

HBV_STATES = (
    "Si",
    "Su",
    "Sf",
    "Ss",
    "Sp",
)

class HBVMethods(eWaterCycleModel):
    """
    The eWatercycle HBV model.
    """

    forcing: LumpedMakkinkForcing | CaravanForcing  # The model requires forcing.
    parameter_set: None  # The model has no parameter set.

    _config: dict = {
        "precipitation_file": "",
        "potential_evaporation_file": "",
        "mean_temperature_file": "",
        "parameters": "",
        "initial_storage": "",
    }

    def _make_cfg_file(self, **kwargs) -> Path:
        """Write model configuration file."""

        if "parameters" not in kwargs:
            msg = (
                "The model needs the parameters argument, consisting of 9 parameters;\n"
                "   [Imax, Ce, Sumax, Beta, Pmax, Tlag, Kf, Ks, FM]"
            )
            raise ValueError(msg)

        if  len(list(kwargs["parameters"])) != 9:
            msg = (
                "Incorrect number of parameters provided."
            )
            raise ValueError(msg)

        self._config["parameters"] = list(kwargs["parameters"])

        if "initial_storage" in kwargs:
            if len(list(kwargs["initial_storage"])) != 5:
                msg = "The model needs 5 initial storage terms."
                raise ValueError(msg)

            self._config["initial_storage"] = list(kwargs["initial_storage"])
        else:
            self._config["initial_storage"] = [0, 0, 0, 0, 0]

        # HBV does not expect a JSON array, but instead a comma separated string;
        self._config["initial_storage"] = ",".join(str(el) for el in self._config["initial_storage"])
        self._config["parameters"] = ",".join(str(el) for el in self._config["parameters"])

        self._config["precipitation_file"] = str(
            self.forcing.directory / self.forcing['pr']
        )
        self._config["potential_evaporation_file"] = str(
            self.forcing.directory / self.forcing['evspsblpot']
        )
        self._config["mean_temperature_file"] = str(
            self.forcing.directory / self.forcing['tas']
        )

        config_file = self._cfg_dir / "HBV_config.json"

        with config_file.open(mode="w") as f:
            f.write(json.dumps(self._config, indent=4))

        return config_file

    @property
    def parameters(self) -> ItemsView[str, Any]:
        """List the (initial!) parameters for this model.

        Exposed HBV parameters:
            Imax (mm): is the maximum amount of interception, under the assumption that all interception evaporates

            Ce(−): is a parameter used to describe what factor actually evaporates from the ground
                  (Unsaturated root zone: 𝑆𝑢) and is 𝐸𝐴=𝑆𝑢𝑆𝑢,𝑚𝑎𝑥×𝐶𝑒𝐸𝑝

            Sumax(mm): Is the size of the reservoir of the unsaturated root zone (𝑆𝑢)
                    i.e. the amount of water the top layer of soil can hold. This parameter is used in a few other calculations.

            Beta (−): is a factor controlling the split between fast and slow flow (overland vs groundwater).
                    Some water will be held by the soil whilst some flows over it and straight to the river.
                    𝐶𝑟=(𝑆𝑢/𝑆𝑢_𝑚𝑎𝑥)^𝛽 which is used to determine the water infiltrating: 𝑄𝑖𝑢=(1−𝐶𝑟)𝑃𝑒
                    where 𝑃𝑒 is the actual precipitation reaching the ground.
                    The rest flow into the fast reservoir 𝑄𝑢𝑓 – which is the groundwater.

            Pmax (mm): is the maximum amount of percolation which can occur from the ground
                       to the deeper groundwater flow: 𝑄𝑢𝑠=𝑃𝑚𝑎𝑥(𝑆𝑢𝑆𝑢,𝑚𝑎𝑥)

            T_lag (d): is the lag time between water falling and reaching the river.

            Kf (-): the fast flow is modelled as a linear reservoir thus a fraction
                    of the volume stored leaves to the river 𝑄𝑓=𝐾𝑓∗𝑆𝑓

            Ks (−): Similarly the slow flow is also modelled as 𝑄𝑆=𝐾𝑠∗𝑆𝑆.

            FM (mm/deg/d): Melt Factor: mm of melt per deg per day

        """
        pars: dict[str, Any] = dict(zip(HBV_PARAMS, self._config["parameters"].split(',')))
        return pars.items()

    @property
    def states(self) -> ItemsView[str, Any]:
        """List the (initial!) states for this model.

        Exposed HBV states:
            Si (mm): Interception storage, water stored in leaves
            Su (mm): Unsaturated rootzone storage, water stored accessible to plants
            Sf (mm): Fastflow storage, moving Fast through the soil - preferential flow paths, upper level
            Ss (mm): Groundwater storage, moving Slowly through the soil - deeper grounds water.
            Sp (mm): SnowPack Storage, amount of snow stored

        """
        pars: dict[str, Any] = dict(zip(HBV_STATES, self._config["initial_storage"].split(',')))
        return pars.items()


    def finalize(self) -> None:
        """Perform tear-down tasks for the model.

        After finalization, the model should not be used anymore.
        """
        # remove bmi
        self._bmi.finalize()
        del self._bmi


class HBV(ContainerizedModel, HBVMethods):
    """The HBV eWaterCycle model, with the Container Registry docker image."""
    bmi_image: ContainerImage = ContainerImage(
        "ghcr.io/ewatercycle/hbv-bmi-grpc4bmi:latest"
    )

# class HBVLocal(LocalModel, HBVMethods):
#     """The HBV eWaterCycle model, with the local BMI."""
#     bmi_class: Type[Bmi] = import_bmi()
