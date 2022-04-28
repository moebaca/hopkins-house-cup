import aws_cdk as core
import aws_cdk.assertions as assertions

from hopkins_house_cup.hopkins_house_cup_stack import HopkinsHouseCupStack

# example tests. To run these tests, uncomment this file along with the example
# resource in hopkins_house_cup/hopkins_house_cup_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = HopkinsHouseCupStack(app, "hopkins-house-cup")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
