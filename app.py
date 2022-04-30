#!/usr/bin/env python3
import os
import aws_cdk as cdk

from hopkins_house_cup.hopkins_house_cup_stack import HopkinsHouseCupStack

app = cdk.App()
HopkinsHouseCupStack(app, "HopkinsHouseCupStack",
    env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')),
)

app.synth()