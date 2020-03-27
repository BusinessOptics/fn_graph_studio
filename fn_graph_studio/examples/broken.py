#%%
import sys
from pathlib import Path
from random import choice, random

import pandas as pd
import numpy as np
import plotly.express as px
import math

from fn_graph import Composer
from fn_graph_studio import run_studio

prices = [random() * 100_000 + 50000 for _ in range(10)]

f = (
    Composer()
    .update(
        wave=lambda frequency, amplitude: pd.DataFrame(dict(x=range(501))).assign(
            y=lambda df: amplitude
            * np.cos(df.x / 500 * math.pi * 3)
            * np.sin(df.x / 500 * math.pi * frequency)
        ),
        plot=lambda wave: px.line(wave, x="x", y="y"),
        broken=lambda wave, missing: wave,
    )
    .update_parameters(frequency=(float, 1), amplitude=(float, 1))
)

# %%
