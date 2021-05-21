from ruamel.yaml import YAML

from . import default, hype, lisflood, marrmot, pcrglobwb, wflow
from .preprocessors import RecipeGenerator

FORCING_CLASSES = defaultdict(default.DefaultForcing, wflow=wflow.WflowForcing)

FORCING_GENERATORS = {
    'hype':
    RecipeGenerator(model='hype',
                    update_func=hype.update_recipe,
                    recipe_name='hydrology/recipe_hype.yml'),
    'lisflood':
    RecipeGenerator(model='lisflood',
                    update_func=lisflood.update_recipe,
                    recipe_name='hydrology/recipe_lisflood.yml'),
    'marrmot':
    RecipeGenerator(model='marrmot',
                    update_func=marrmot.update_recipe,
                    recipe_name='hydrology/recipe_marrmot.yml'),
    'pcrglobwb':
    RecipeGenerator(model='pcrglobwb',
                    update_func=pcrglobwb.update_recipe,
                    recipe_name='hydrology/recipe_pcrglobwb.yml'),
    'wflow':
    RecipeGenerator(model='wflow',
                    update_func=wflow.update_recipe,
                    recipe_name='hydrology/recipe_wflow.yml')
}


def generate(target_model: str, **kwargs):
    """Generate forcing data for model evaluation.

    Args:
        target_model: Name of the model
        **kwargs: Model specific recipe settings

    Returns:
        :obj:`ForcingData`
    """
    recipe_generator = FORCING_GENERATORS[target_model]
    recipe = recipe_generator(**kwargs)
    recipe_output = recipe.run()

    Forcing = FORCING_CLASSES[target_model]
    return Forcing.from_recipe(recipe_output=recipe_output, **kwargs)


def load(target_model, **kwargs):
    """Load existing forcing data from disk.

    Args:
        target_model: Name of the hydrological model for which the forcing will be used
        **kwargs: Model specific configuration settings related to the forcing data

    Returns:
        :obj:`ForcingData`
    """
    Forcing = FORCING_CLASSES[target_model]
    return Forcing(**kwargs)


def reload(directory):
    """Reload previously generated forcing data.

    Args:
        directory: forcing data directory; must contain `ewatercycle_forcing.yaml`
    """
    yaml = YAML()
    source = Path(directory) / 'ewatercycle_forcing.yaml'
    data = yaml.load(source)

    target_model = data.pop('model')
    Forcing = FORCING_CLASSES[target_model]
    return Forcing(**data)
