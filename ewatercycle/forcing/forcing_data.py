class ForcingData(object):
    """Container for forcing data."""
    def __init__(self, recipe_output):
        self.recipe_output = recipe_output

    @property
    def location(self):
        """Return forcing directory."""
        return self.recipe_output.session.session_dir
