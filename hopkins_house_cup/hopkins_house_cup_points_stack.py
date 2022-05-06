from aws_cdk import (
    Stack,
)
from aws_cdk.aws_iam import (
    Role,
    ServicePrincipal,
    ManagedPolicy
)
from aws_cdk.aws_certificatemanager import (
    DnsValidatedCertificate
)
from aws_cdk.aws_lambda import (
    Function,
    Runtime,
    Code
)
from aws_cdk.aws_route53 import (
    ARecord,
    RecordTarget,
    HostedZone
)
from aws_cdk.aws_apigateway import (
    LambdaRestApi,
    DomainNameOptions,
    CorsOptions
)
from aws_cdk.aws_route53_targets import (
    ApiGateway
)
from constructs import Construct

###
# This stack instantiates an API GW endpoint with Lambda proxy integration which will reach
# out to DynamoDB and grab the current score for the house cup. 
###
class HopkinsHouseCupsPointsStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Must register this domain name in Route53
        domain_name = 'hopkinshousecup.com'
        zone = HostedZone.from_lookup(
            self, 'HouseCupZone', domain_name=domain_name)

        # Create role that will allow Lambda to execute
        lambda_role = Role(self, 'GetHouseCupPointsLambdaRole',
                           assumed_by=ServicePrincipal('lambda.amazonaws.com'),
                           managed_policies=[
                               ManagedPolicy.from_aws_managed_policy_name(
                                   'service-role/AWSLambdaBasicExecutionRole')
                           ]
                           )
        # Create Lambda function 
        handler = Function(self, "GetHouseCupPointsLambda",
                           role=lambda_role,
                           runtime=Runtime.NODEJS_14_X,
                           code=Code.from_asset("lambda_fns"),
                           handler="housepoints.handler"
                           )
        
        # TLS certificate for use with website
        certificate = DnsValidatedCertificate(self, 'HopkinsHouseCupCertificate',
                                              domain_name=domain_name,
                                              subject_alternative_names=[
                                                  '*.' + domain_name
                                              ],
                                              hosted_zone=zone,
                                              region='us-east-1',
                                              )
        
        # Create API Gateway with Lambda proxy 
        api = LambdaRestApi(self, "HouseCupPointsAPI",
                            handler=handler,
                            default_cors_preflight_options=CorsOptions(
                                allow_origins=[
                                    f"https://{domain_name}",
                                    f"https://www.{domain_name}",
                                    f"https://api.{domain_name}"
                                ],
                                allow_methods=['GET']
                            ),
                            domain_name=DomainNameOptions(
                                domain_name=f"api.{domain_name}",
                                certificate=certificate)
                            )

        # Route53 Alias record for the API Gateway API endpoint
        ARecord(self, "APIAliasRecord",
                record_name=f"api.{domain_name}",
                target=RecordTarget.from_alias(ApiGateway(api)),
                zone=zone
                )
