# TODO: We need a real example here

import sys
from pathlib import Path
from random import choice, random
import logging

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from fn_graph import Composer
from fn_graph_studio import run_studio

logging.basicConfig(level=logging.DEBUG)

default_model = Composer().update_parameters(internal_default_rate=0.1)
house_pricing = Composer().update_parameters(price=1000)
loan_pricing = (
    Composer()
    .link(
        house_price="house_pricing__price",
        default_rate="default_model__internal_default_rate",
    )
    .update(
        some_random_number=lambda house_price, default_rate: house_price * default_rate
    )
)

f = (
    Composer()
    .update_namespaces(house_pricing=house_pricing, default_model=default_model)
    .update_from(loan_pricing)
)

run_studio(f.development_cache(__name__))
