#!/usr/bin/env python3
import aws_cdk as cdk

from hopkins_house_cup.hopkins_house_cup_stack import HopkinsHouseCupStack

app = cdk.App()
HopkinsHouseCupStack(app, "HopkinsHouseCupStack",
    env=cdk.Environment(account=app.node.try_get_context('account_id'), region='us-east-1'),
)

app.synth()