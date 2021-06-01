from . import preprocessors
from .forcing_data import ForcingData


def generate(model: str, **kwargs):
    """
    Generate forcing data for model evaluation.

    Parameters
    ----------
    model : str
        Name of the model
    **kwargs :
        Model specific parameters

    Returns
    -------
    forcing_data : :obj:`ForcingData`
    """
    recipe_generator = preprocessors.MODELS[model]
    recipe = recipe_generator(**kwargs)
    recipe_output = recipe.run()

    return ForcingData(recipe_output)
