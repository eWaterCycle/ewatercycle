from pathlib import Path
from typing import Any, Callable, Dict

from esmvalcore.experimental import get_recipe

class RecipeGenerator:
    def __init__(self, model: str, update_func: Callable, recipe_name: str):
        self.recipe_name = recipe_name
        self.update_func = update_func
        self.model = model
        self.recipe = get_recipe(recipe_name)
        self.supported_datasets = {
            'ERA5': {
                'dataset': 'ERA5',
                'project': 'OBS6',
                'tier': 3,
                'type': 'reanaly',
                'version': 1
            },
            'ERA-Interim': {
                'dataset': 'ERA-Interim',
                'project': 'OBS6',
                'tier': 3,
                'type': 'reanaly',
                'version': 1
            },
        }

    def __call__(self, **kwargs):
        """Return recipe updated with new keyword arguments."""
        if kwargs.get('dataset') is not None:
            kwargs['dataset'] = self.supported_datasets[kwargs['dataset']]

        self.update_func(self.recipe.data, **kwargs)
        return self.recipe

    def __repr__(self):
        """Return canonical class representation."""
        return (f'{self.__class__.__name__}(model={self.model!r}, '
                f'update_func={self.update_func!r}, '
                f'recipe_name={self.recipe_name!r})')
