from enum import Enum


class DeploymentMode(str, Enum):
    TEST = "test"
    LOCAL_ONLY = "local_only"
    HOSTED_SAAS = "hosted_saas"
