# TODO: We need a real example here

import sys
from pathlib import Path
from random import choice, random

import pandas as pd
from fn_graph import Composer

from fn_graph_studio import run_studio

default_model = Composer().update_parameters(internal_default_rate=0.1)
house_pricing = Composer().update_parameters(price=(int, 1000))
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
    .update_parameters(a__b__c__d=(int, 1), a__b__c__a=(str, "a"), a__b__x=(str, "x"))
    .update_parameters(steve=1)
)
