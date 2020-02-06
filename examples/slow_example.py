import sys
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from fn_graph import Composer
from fn_graph_studio import run_studio

f = (
    Composer()
    .update(
        a=lambda size: pd.DataFrame(dict(x=range(size))),
        b=lambda a: a.assign(x=lambda df: df.x / df.x.count() * 2 * 3.14),
        c=lambda b: b.assign(y=np.sin(b.x)),
        d=lambda c, a: a.merge(c, on="x", how="outer"),
    )
    .update_parameters(size=100000)
)

run_studio(f)
