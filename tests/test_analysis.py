from ewatercycle.analysis import hydrograph
from matplotlib.testing.decorators import image_comparison
import pandas as pd
import numpy as np


@image_comparison(
    baseline_images=['hydrograph'],
    remove_text=True,
    extensions=['png'],
    savefig_kwarg={'bbox_inches':'tight'},
)
def test_hydrograph():
    ntime = 300

    dti = pd.date_range("2018-01-01", periods=ntime, freq="d")

    np.random.seed(20210416)

    discharge = {
        'discharge_a': pd.Series(np.linspace(0, 2, ntime), index=dti),
        'discharge_b': pd.Series(3*np.random.random(ntime)**2, index=dti),
        'discharge_c': pd.Series(2*np.random.random(ntime)**2, index=dti),
        'reference': pd.Series(np.random.random(ntime)**2, index=dti),
    }

    df = pd.DataFrame(discharge)

    precipitation = {
        'precipitation_a': pd.Series(np.random.random(ntime)/20, index=dti),
        'precipitation_b': pd.Series(np.random.random(ntime)/30, index=dti),
    }

    df_pr = pd.DataFrame(precipitation)

    hydrograph(df, reference='reference', precipitation=df_pr)
