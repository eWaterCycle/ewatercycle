# This shows how the new API will be used by external plugin developers and end users.
# Can be removed or moved to documentation after finishing PR

#############################
# In external plugin package:


class LeakyBucketMixins:
    # Define here custom functionality for your model.
    # By using a mixin we don't have to write it twice (for local/containerized)

    # Set self.parameters as seen fit
    def parameters(self, *args, **kwargs):
        super.setup()


class _LeakyBucketDevelopment(LeakyBucketMixins, eWaterCycle.LocalModel):
    bmi_class = LeakyBucketBmi
    # Usually, you shouldn't have to change anything else


class LeakyBucket(LeakyBucketMixins, ewatercycle.ContainerizedModel):
    bmi_image = "ghcr.io/ewatercycle/leakybucket-grpc4bmi:latest"
    # If necessary, override self.make_bmi_instance


#######################################
# As a user of external plugin package:

LeakyBucket = ewatercycle.models.get("LeakyBucket")  # plugin found via entrypoint
from ewc_leaky import (  # development version shipped with plugin package
    LeakyBucketDevelopment,
)

model = LeakyBucket(forcing=..., parameter_set=...)
model = LeakyBucket(
    forcing=...,
    parameter_set=...,
    image="ghcr.io/ewatercycle/leakybucket-grpc4bmi:v0.0.1",
)
model = _LeakyBucketDevelopment(
    forcing=..., parameter_set=..., bmi_class=LeakyBucketBmi
)
